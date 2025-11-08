from sqlalchemy.orm import Session

from App.card.services import CardService
from App.decks.discard_deck_service import DiscardDeckService
from App.card.services import CardService
from App.decks.draft_deck_service import DraftDeckService
from App.events.enums import Direction, EventType
from App.events.services import EventManager
from App.events.models import Event as GameEvent
from App.exceptions import (
    GameIsBlocked,
    GameNotFoundError,
    InSocialDisgraceException,
    InvalididDetectiveSet,
    NotCardInHand,
    NotPlayableCard,
    NotPlayersTurnError,
    ObligatoryDiscardError,
    PlayerNotFoundError,
    PlayerHave6CardsError,
    DeckNotFoundError,
    SecretAlreadyRevealedError,
    SecretNotFoundError,
    SecretNotRevealed)
from App.games.models import Game
from App.games.services import GameService
from App.games.enums import ActionStatus, GameStatus, Winners
from App.players.utils import sort_players
from App.secret.enums import SecretType
from App.secret.services import relate_secret_player, reveal_secret, unrelate_secret_player
from App.players.models import Player
from App.players.enums import PlayerRole, TurnAction, TurnStatus
from App.players.services import PlayerService
from App.sets.enums import DetectiveSetType
from App.sets.models import DetectiveSet
from App.sets.services import DetectiveSetService
from App.card.models import Card, Instant, Event as EventCard
from App.events.services import EventManager
from App.events.enums import EventType
from App.sets.enums import DetectiveSetType

class PlayService:

    def __init__(self, db: Session):
        self._db = db
        self._game_service = GameService(db)
        self._player_service = PlayerService(db)
        self._card_service = CardService(db)
        self._discard_deck_service = DiscardDeckService(db)
        self._detective_set_service = DetectiveSetService(db)
        self._event_managaer = EventManager(db)

    def no_action(
            self,
            game_id: int,
            player_id: int,
        ) -> Game:
        game: Game | None = self._game_service.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(f"No game found {game_id}")

        player: Player | None = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        if player.turn_status != TurnStatus.PLAYING:
            raise NotPlayersTurnError(f"It's not the turn of player {player_id}")
        
        player.turn_status = TurnStatus.DISCARDING
        
        self._db.add(player)
        self._db.flush()
        self._db.commit()
        
        return game

    def play_card(self, game, player_id, card_id) -> tuple[Card,TurnAction]:
        player = self._db.query(Player).filter(Player.id == player_id).first()

        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        if player.turn_status != TurnStatus.PLAYING:
            raise NotPlayersTurnError(f"It's not the turn of player {player_id}")
        
        if card_id not in [card.id for card in player.cards]:
            raise NotCardInHand("That card does not belong to the player.")
        
        card = self._card_service.get_card(card_id)
        if not isinstance(card, EventCard):
            raise NotPlayableCard("You tried to play a card that is not playable.")
        
        self._card_service.unrelate_card_player(card_id, player_id)
        if card.name != "Early Train to Paddington" and card.name != "Delay the Muderer's Escape":
            self._discard_deck_service.relate_card_to_discard_deck(game.discard_deck.id, card)

        turn_status = self._card_service.select_event_type(game, player, card)

        cancelable = True
        if card.name == "Cards off the table":
            cancelable = False

        event = self._event_managaer.create(
            type=EventType.PLAY_CARD,
            game=game,
            main_player=player,
            played_card=card
        )

        if cancelable:
            game.action_status = ActionStatus.UNBLOCKED

            for p in game.players:
                p.turn_action = TurnAction.PLAY_NSF
            
        self._db.flush()
        self._db.commit()

        return card, turn_status

    def play_set(self, game: Game, player_id, card_ids):
        player = self._db.query(Player).filter(Player.id == player_id).first()

        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        cards = player.cards
                
        if player.turn_status != TurnStatus.PLAYING:
            raise NotPlayersTurnError(f"It's not the turn of player {player_id}")
        played_cards = [card for card in player.cards if card.id in card_ids]
        set_type = self._detective_set_service.validate_play_set(played_cards)
        if not set_type:
            raise InvalididDetectiveSet("Not a valid detective set. Learn the rules little cheater.")

        new_set = self._detective_set_service.create_detective_set(player_id, card_ids, set_type)
        
        cancelable = True
        if new_set.type == DetectiveSetType.SIBLINGS_BERESFORD:
            cancelable = False
        
        event = self._event_managaer.create(
            type=EventType.PLAY_SET,
            game=game,
            main_player=player,
            dset=new_set,
            cancelable=cancelable
        )

        if cancelable:
            game.action_status = ActionStatus.UNBLOCKED

            for p in game.players:
                p.turn_action = TurnAction.PLAY_NSF

        self._db.flush()
        self._db.commit()

        return new_set
    
    def play_nsf(self, game: Game, player: Player, card_id: int | None):

        if game.action_status == ActionStatus.BLOCKED:
            raise GameIsBlocked("It's not the time to play a Not So Fast")

        if player.turn_action != TurnAction.PLAY_NSF:
            raise NotPlayersTurnError(f"You are playing Too Fast, can't play Not So Fast right now.")
        

        if card_id is None:
            player.turn_action = TurnAction.NO_ACTION
            self._db.flush()
            self._db.commit()
            return None


        if card_id not in [card.id for card in player.cards]:
            raise NotCardInHand("That card does not belong to the player.")
        
        card = self._card_service.get_card(card_id)
        if not isinstance(card, Instant):
            raise NotPlayableCard("You tried to play a card that is not playable.")
        
        self._card_service.unrelate_card_player(card_id, player.id)

        game.action_status = ActionStatus.BLOCKED
        for p in game.players:
            p.turn_action = TurnAction.NO_ACTION
        
        self._db.flush()
        self._db.commit()

        event = self._event_managaer.create(
            type=EventType.PLAY_NSF,
            game=game,
            main_player=player,
            played_card=card
        )

        return event , card
    
    def restart_nsf(self, game: Game):
        game.action_status = ActionStatus.UNBLOCKED
        for p in game.players:
            p.turn_action = TurnAction.PLAY_NSF

        self._db.flush()
        self._db.commit()

        return None

    def steal_set(
            self,
            player_id: int,
            stolen_player_id: int,
            set_id: int
    ):
        
        player = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        stolen_player = self._db.query(Player).filter(Player.id == stolen_player_id).first()
        if not stolen_player:
            raise PlayerNotFoundError(f"Player {stolen_player_id} not found")
        
        if set_id not in [dset.id for dset in stolen_player.sets]:
            raise InvalididDetectiveSet(f"Detective set {set_id} not found")
        
        dset = next((dset for dset in stolen_player.sets if dset.id == set_id))
        
        stolen_player.sets.remove(dset)
        player.sets.append(dset)

        player.turn_status = TurnStatus.DISCARDING_OPT
        player.turn_action = TurnAction.NO_ACTION

        self._db.flush()
        self._db.commit()

        return dset

    def discard(
            self,
            game: Game,
            player_id: int,
            cards_id: list[int]
        ):

        player = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        if player.turn_status not in [TurnStatus.DISCARDING, TurnStatus.DISCARDING_OPT]:
            raise NotPlayersTurnError(f"It's not the turn of player {player_id}")
        
        if len(player.cards) == 0:
            player.turn_status = TurnStatus.DRAWING
            return []
        
        if not player.in_social_disgrace and len(cards_id) == 0 and player.turn_status == TurnStatus.DISCARDING:
            raise ObligatoryDiscardError(f"Player {player_id} must discard at least one card")
        
        if player.in_social_disgrace and len(cards_id) > 1:
            raise InSocialDisgraceException(f"Player {player_id} must discard only one card")

        discarded_cards = []
        
        if player.in_social_disgrace and len(player.cards) == 0:
            player.turn_status = TurnStatus.DRAWING
            return []

        discarded_cards = []

        for card_id in cards_id:
            card = self._card_service.get_card(card_id)
            discarded_cards.append(card)
            card = self._player_service.discard_card(player_id, card)
            if card.name != "Early Train to Paddington" and card not in player.cards:
                self._discard_deck_service.relate_card_to_discard_deck(game.discard_deck.id, card)
            else:
                pass
                #self.early_train_to_paddington(game, player)
        
    
        player.turn_status = TurnStatus.DRAWING
        if len(player.cards) == 6:
            self.end_turn(game.id,player.id)

            
        self._db.add(player)
        self._db.flush()
        self._db.commit()
        return discarded_cards

    def draw_card_from_deck(self, game_id, player_id):

        game = self._db.query(Game).filter_by(id=game_id).first()
        rep_deck = game.reposition_deck # type: ignore
        player = self._db.query(Player).filter_by(id=player_id).first()

        if player.turn_status != TurnStatus.DRAWING: # type: ignore
            raise NotPlayersTurnError(f"It's not the turn of player {player_id} for discard")

        if rep_deck is None:
            raise DeckNotFoundError(f"Game {game_id} doesn't have a reposition deck")  
        
        if player is None:
            raise PlayerNotFoundError(f"Player {player_id} not found")
              
        if len(player.cards) == 6:
            raise PlayerHave6CardsError(f"Player {player_id} already has 6 cards")

        if rep_deck.number_of_cards == 0:
            return None

        card = max(rep_deck.cards, key=lambda c: c.order)  # type: ignore

        CardService(self._db).unrelate_card_reposition_deck(rep_deck.id, card.id, commit=True)
        CardService(self._db).relate_card_player(player_id, card.id, commit=True)

        self._db.commit()
        self._db.refresh(rep_deck)
        self._db.refresh(player)
        self._db.refresh(card)

        return card

    def end_turn(
            self,
            game_id: int,
            player_id: int,
        ) -> tuple[Game, Player]:
        game: Game | None = self._game_service.get_by_id(game_id)
        if not game: 
            raise GameNotFoundError(f"No game found {game_id}")

        player: Player | None = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        if player.turn_status != TurnStatus.DRAWING:
            raise NotPlayersTurnError(f"Player {player_id} cannot end turn now")
        # if len(player.cards) != 6:
        #     raise PlayerNeedSixCardsError(f"Player {player_id} needs to have six cards to end turn")
        
        player.turn_status = TurnStatus.WAITING
        game.turn_number += 1
        
        GameService(self._db).select_player_turn(game_id)
        
        self._db.add(player)
        self._db.add(game)
        self._db.flush()
        self._db.commit()

        return game, player

    def end_game(self, game_id: int) -> Game:
        game: Game | None = self._game_service.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(f"No game found {game_id}")

        deck = game.reposition_deck
        if len(deck.cards) == 0:
            game.status = GameStatus.FINISHED
            game.winners = Winners.MURDERER

        murderer = next(player for player in game.players if player.role == PlayerRole.MURDERER)
        murderer_secret = next((secret for secret in murderer.secrets if secret.type == SecretType.MURDERER), None)
        if not murderer_secret or murderer_secret.revealed:
            game.status = GameStatus.FINISHED
            game.winners = Winners.DETECTIVE

        detectives: list[Player] = [player for player in game.players if player.role == PlayerRole.DETECTIVE]
        if all(detective.in_social_disgrace for detective in detectives):
            game.status = GameStatus.FINISHED
            game.winners = Winners.MURDERER

        self._db.add(game)
        self._db.flush()
        self._db.commit()

        return game

    def select_any_player(self, game_id: int, player_id: int, selected_player_id: int):
        game: Game | None = self._game_service.get_by_id(game_id)
        if not game:
            raise GameNotFoundError(f"No game found {game_id}")

        player: Player | None = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        if (player.turn_action != TurnAction.SELECT_ANY_PLAYER
            and player.turn_action != TurnAction.CARDS_OFF_THE_TABLE
            and player.turn_action != TurnAction.SATTERWAITEWILD):
            raise NotPlayersTurnError(f"Player {player_id} cannot select any player now")
        
        player_in_game = GameService(self._db).player_in_game(game_id, selected_player_id)
        if not player_in_game:
            raise PlayerNotFoundError(f"Selected player {selected_player_id} not found in game {game_id}")
        
        selected_player: Player | None = self._db.query(Player).filter(Player.id == selected_player_id).first()
        if not selected_player:
            raise PlayerNotFoundError(f"Selected player {selected_player_id} not found")
        
        selected_player_in_game = GameService(self._db).player_in_game(game_id, selected_player_id)
        if not selected_player_in_game:
            raise PlayerNotFoundError(f"Selected player {selected_player_id} not found in game {game_id}")
        
        event = player.turn_action
        current_turn_player = None
        
        for p in game.players:
            if p.turn_status == TurnStatus.TAKING_ACTION:
                current_turn_player = p

        if not current_turn_player:
            raise PlayerNotFoundError(f"Current player not found")
        
        countNotSoFast = None
        if event == TurnAction.CARDS_OFF_THE_TABLE:
            pass
            countNotSoFast = self.cards_off_the_tables(game, player, selected_player)


        elif event == TurnAction.SELECT_ANY_PLAYER:
            player.turn_action = TurnAction.NO_ACTION

            if selected_player.in_social_disgrace:
                selected_player.turn_action = TurnAction.NO_ACTION
                current_turn_player.turn_status = TurnStatus.DISCARDING_OPT
                event = TurnAction.NO_ACTION
            else:
                selected_player.turn_action = TurnAction.REVEAL_OWN_SECRET

        elif event == TurnAction.SATTERWAITEWILD:
            player.turn_action = TurnAction.WAITING_ACTION
            if selected_player.in_social_disgrace:
                selected_player.turn_action = TurnAction.NO_ACTION
                current_turn_player.turn_status = TurnStatus.DISCARDING_OPT
                event = TurnAction.NO_ACTION
            else:
                selected_player.turn_action = TurnAction.GIVE_SECRET_AWAY

            

        self._db.flush()
        self._db.commit()

        return game, player, selected_player, event, countNotSoFast

    def cards_off_the_tables(self, game: Game, player: Player, selected_player: Player) -> int:
        countNotSoFast = 0

        cards_player = list(selected_player.cards)
        for card in cards_player:
            if card.name == "Not so Fast!":
                card = PlayerService(self._db).discard_card(selected_player.id, card)
                DiscardDeckService(self._db).relate_card_to_discard_deck(game.discard_deck.id, card)
                countNotSoFast = countNotSoFast + 1
        
        player.turn_action = TurnAction.NO_ACTION
        player.turn_status = TurnStatus.DISCARDING_OPT
        self._db.flush()
        self._db.commit()
        
        return countNotSoFast

    def draw_card_from_draft(self, game_id, player_id, order):
        game = self._db.query(Game).filter_by(id=game_id).first()
        draft_deck = game.draft_deck
        rep_deck = game.reposition_deck
        player = self._db.query(Player).filter_by(id=player_id).first()


        if player.turn_status != TurnStatus.DRAWING:
            raise NotPlayersTurnError(f"It's not the turn of player {player_id} for discard")

        if draft_deck is None:
            raise DeckNotFoundError(f"Game {game_id} doesn't have a draft deck")  
        
        if player is None:
            raise PlayerNotFoundError(f"Player {player_id} not found")  
              
        card = None
        for c in draft_deck.cards:
            if c.order == order:
                card = c
                break
        

        DraftDeckService(self._db).unrelate_card_from_draft_deck(draft_deck.id, card)
        CardService(self._db).relate_card_player(player_id, card.id, commit=True)

        self._db.commit()
        self._db.refresh(draft_deck)
        self._db.refresh(player)
        self._db.refresh(card)

        card1 = max(rep_deck.cards, key=lambda c: c.order)  # type: ignore
        CardService(self._db).unrelate_card_reposition_deck(rep_deck.id, card1.id, commit=True)
        DraftDeckService(self._db).relate_card_to_draft_deck(draft_deck.id, card1, order)

        self._db.commit()
        self._db.refresh(draft_deck)
        self._db.refresh(rep_deck)
        self._db.refresh(card1)

        return card

    def reveal_secret_service(self, game, player_id: int, secret_id: int, revealed_player_id: int):

        player = self._db.query(Player).filter(Player.id == player_id).first()
        revealed_player = self._db.query(Player).filter(Player.id == revealed_player_id).first()
        players = game.players

        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        if not revealed_player:
            raise PlayerNotFoundError(f"Player {revealed_player_id} not found")

        if player.turn_action != TurnAction.REVEAL_SECRET:
            raise NotPlayersTurnError(f"Player {player_id} cannot reveal secret now")

        secret = None
        for s in revealed_player.secrets:
            if s.id == secret_id:
                secret = s
                break
        
        if not secret:
            raise SecretNotFoundError(f"Secret {secret_id} not found for player {player_id}")
        
        if secret.revealed:
            raise SecretAlreadyRevealedError(f"Secret {secret_id} already revealed")

        # TODO: ACA HAY CASO DESGRACIA SOCIAL
        reveal_secret(secret, self._db)
        self._player_service.set_social_disgrace(revealed_player)
        current_turn_player = None

        for p in players:
            if p.turn_status == TurnStatus.TAKING_ACTION:
                current_turn_player = p
        
        if not current_turn_player:
            raise PlayerNotFoundError(f"Player not found")
        
        print(current_turn_player.id)
        current_turn_player.turn_status = TurnStatus.DISCARDING_OPT
        player.turn_action = TurnAction.NO_ACTION

        self._db.commit()
        self._db.refresh(player)
        self._db.refresh(secret)
        self._db.refresh(revealed_player)
        self._db.refresh(current_turn_player)

        return secret

    def hide_secret(self, game, player_id, secret_id, affected_player_id):

        player = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        if player.turn_action != TurnAction.HIDE_SECRET:
            raise NotPlayersTurnError(f"Player {player_id} cannot hide secret now")
        
        affected_player = self._db.query(Player).filter(Player.id == affected_player_id).first()
        if not affected_player:
            raise PlayerNotFoundError(f"Player {affected_player_id} not found")
        
        if secret_id not in [secret.id for secret in affected_player.secrets]:
            raise SecretNotFoundError(f"Secret id {secret_id} not found")
        
        secret = next((secret for secret in affected_player.secrets if secret.id == secret_id))

        if not secret.revealed:
            raise SecretNotRevealed(f"Secret id {secret_id} is not revealed")
        
        # TODO: ACA HAY CASO DESGRACIA SOCIAL
        secret.revealed = False
        self._db.flush()
        self._db.commit()
        self._player_service.set_social_disgrace(affected_player)

        players = game.players
        current_turn_player = None

        for p in players:
            if p.turn_status == TurnStatus.TAKING_ACTION:
                current_turn_player = p

        if not current_turn_player:
            raise PlayerNotFoundError(f"Player not found")

        current_turn_player.turn_status = TurnStatus.DISCARDING_OPT
        player.turn_action = TurnAction.NO_ACTION

        self._db.flush()
        self._db.commit()
        
        return secret

    def and_then_there_was_one_more_effect(self, 
                                           player_id,
                                           secret_id,
                                           stolen_player_id,
                                           selected_player_id):
        player = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        if player.turn_action != TurnAction.ONE_MORE:
            raise NotPlayersTurnError(f"Player {player_id} cannot hide secret now")
        
        stolen_player = self._db.query(Player).filter(Player.id == stolen_player_id).first()
        if not stolen_player:
            raise PlayerNotFoundError(f"Player {stolen_player_id} not found")
        
        selected_player = self._db.query(Player).filter(Player.id == selected_player_id).first()
        if not selected_player:
            raise PlayerNotFoundError(f"Player {selected_player_id} not found")
        
        if secret_id not in [secret.id for secret in stolen_player.secrets]:
            raise SecretNotFoundError(f"Secret id {secret_id} not found")
        
        secret = next((secret for secret in stolen_player.secrets if secret.id == secret_id))

        if not secret.revealed:
            raise SecretNotRevealed(f"Secret id {secret_id} is not revealed")
        
        # TODO: ACA HAY CASO DESGRACIA SOCIAL
        secret.revealed = False
        self._db.flush()
        self._db.commit()
        unrelate_secret_player(stolen_player, secret, self._db)
        PlayerService(self._db).set_social_disgrace(stolen_player)
        relate_secret_player(selected_player, secret, self._db)
        PlayerService(self._db).set_social_disgrace(selected_player)
        
        player.turn_status = TurnStatus.DISCARDING_OPT
        player.turn_action = TurnAction.NO_ACTION

        self._db.flush()
        self._db.commit()
        
        return secret
    
    def look_into_the_ashes_effect(self, game, player_id, card_id):
        player = self._db.query(Player).filter(Player.id == player_id).first()

        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        if player.turn_action != TurnAction.LOOK_INTO_THE_ASHES:
            raise NotPlayersTurnError(f"Player {player_id} cannot look into the ashes now")
        
        discard_deck = game.discard_deck

        if not discard_deck:
            raise DeckNotFoundError(f"Player {player_id} game does not have a discard deck")
        
        card = None

        for c in discard_deck.cards:
            if c.id == card_id:
                card = c
                break
        
        if not card:
            raise NotCardInHand(f"Card {card_id} not found in discard deck")

        DiscardDeckService(self._db).unrelate_card_from_discard_deck(discard_deck.id, card)
        CardService(self._db).relate_card_player(player_id, card.id, commit=True)

        player.turn_status = TurnStatus.DISCARDING_OPT
        player.turn_action = TurnAction.NO_ACTION

        self._db.flush()
        self._db.commit()
        

        return card
    
    def delay_the_murder_effect(self, game, player_id, cards):

        player = self._db.query(Player).filter(Player.id == player_id).first()
        discard_deck = game.discard_deck
        rep_deck = game.reposition_deck

        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")

        if player.turn_action != TurnAction.DELAY_THE_MURDERER:
            raise NotPlayersTurnError(f"Player {player_id} cannot delay the murder now")

        if not discard_deck:
            raise DeckNotFoundError(f"Game {game.id} does not have a discard deck")
        
        for i in range(len(cards)):

            card = self._db.query(Card).filter(Card.id == cards[-1]).first()

            DiscardDeckService(self._db).unrelate_card_from_discard_deck(discard_deck.id, card)
            CardService(self._db).relate_card_reposition_deck(rep_deck.id, card.id, commit=False)

            cards.pop(-1)


        player.turn_status = TurnStatus.DISCARDING_OPT
        player.turn_action = TurnAction.NO_ACTION

        self._db.flush()
        self._db.commit()
        self._db.refresh(rep_deck)
        self._db.refresh(discard_deck)
        return cards

    def select_own_secret(self, game: Game, player_id: int, secret_id: int):

        player = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        if player.turn_action not in [TurnAction.REVEAL_OWN_SECRET, TurnAction.GIVE_SECRET_AWAY]:
            raise NotPlayersTurnError(f"Player {player_id} cannot reveal secret.")
        
        secret = next((secret for secret in player.secrets if secret.id == secret_id))
        if not secret:
            raise SecretNotFoundError(f"Secret {secret_id} not found for player {player_id}")
        if secret not in player.secrets:
            raise SecretNotFoundError(f"Secret {secret_id} not found for player {player_id}")
        if secret.revealed:
            raise SecretAlreadyRevealedError(f"Secret {secret_id} already revealed")
        
        current_turn_player = None
        waiting_action_player = None

        for p in game.players:
                if p.turn_status == TurnStatus.TAKING_ACTION:
                    current_turn_player = p
                elif p.turn_action == TurnAction.WAITING_ACTION:
                    waiting_action_player = p
        if not current_turn_player:
                raise PlayerNotFoundError(f"Player not found")
        

        secret.revealed = True
        self._db.flush()
        self._db.commit()

        event = player.turn_action

        if event is TurnAction.GIVE_SECRET_AWAY:
            unrelate_secret_player(player, secret, self._db)
            if not waiting_action_player:
                relate_secret_player(current_turn_player, secret, self._db)
            else:
                relate_secret_player(waiting_action_player, secret, self._db)
                waiting_action_player.turn_action = TurnAction.NO_ACTION
            secret.revealed = False

        # TODO: ACA HAY CASO DESGRACIA SOCIAL
        self._player_service.set_social_disgrace(player)
        current_turn_player.turn_status = TurnStatus.DISCARDING_OPT
        player.turn_action = TurnAction.NO_ACTION

        self._db.flush()
        self._db.commit()

        return event, current_turn_player, secret, player

    def get_top_five_discarded_cards(self, player, game_id):
            game = self._db.query(Game).filter_by(id=game_id).first()
            
            if not game:
                raise GameNotFoundError(f"No game found {game_id}")
            
            discard_deck = game.discard_deck
            if not discard_deck:
                raise DeckNotFoundError(f"Game {game_id} does not have a discard deck")
            
            
            sorted_cards = sorted(discard_deck.cards, key=lambda c: c.order, reverse=True)
            
            if player.turn_action == TurnAction.LOOK_INTO_THE_ASHES:
                top_five_cards = sorted_cards[:6]
                top_five_cards.pop(0)
            else:
                top_five_cards = sorted_cards[:5]
            
            return top_five_cards

    def early_train_to_paddington(self, game: Game, player: Player):
            if player.turn_status != TurnStatus.TAKING_ACTION and player.turn_status != TurnStatus.DISCARDING_OPT and player.turn_status != TurnStatus.DISCARDING:
                raise NotPlayersTurnError(f"Player {player.id} cannot use Early Train to Paddington now")
            if player.turn_status == TurnStatus.TAKING_ACTION:
                if player.turn_action != TurnAction.EARLY_TRAIN_TO_PADDINGTON:
                    raise NotPlayersTurnError(f"Player {player.id} cannot use Early Train to Paddington now")
            
            discard_deck = game.discard_deck
            rep_deck = game.reposition_deck
            
            if rep_deck.number_of_cards >= 6:
                for _ in range(6):
                    card = max(rep_deck.cards, key=lambda c: c.order)
                    CardService(self._db).unrelate_card_reposition_deck(rep_deck.id, card.id)
                    self._discard_deck_service.relate_card_to_discard_deck(discard_deck.id, card)
                    
            else:
                while rep_deck.number_of_cards > 0:
                    card = max(rep_deck.cards, key=lambda c: c.order)
                    CardService(self._db).unrelate_card_reposition_deck(rep_deck.id, card.id)
                    self._discard_deck_service.relate_card_to_discard_deck(discard_deck.id, card)

            self.end_game(game.id)

            player.turn_status = TurnStatus.DISCARDING_OPT
            player.turn_action = TurnAction.NO_ACTION

            self._db.flush()
            self._db.commit()

    def add_detective(self, game: Game, player_id: int, set_id: int, card_id: int):

        player = self._db.query(Player).filter_by(id=player_id).first()

        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")

        if player.turn_status != TurnStatus.PLAYING:
            raise NotPlayersTurnError(f"Player {player_id} cannot add detective now")
        
        dset = self._db.query(DetectiveSet).filter(DetectiveSet.id == set_id).first()
        if not dset:
            raise InvalididDetectiveSet(f"Detective set {set_id} not found")
        
        set_cards = dset.cards

        card = CardService(self._db).get_card(card_id)
        new_set = []

        for c in set_cards:
            new_set.append(c)

        new_set.append(card)

        if card.name == "Ariadne Oliver":
            set_type = DetectiveSetType.ARIADNE_OLIVER
        else:
            for c in new_set:
                if c.name == "Ariadne Oliver":
                    new_set.remove(c)
            set_type = self._detective_set_service.validate_play_set(new_set)
        
        if not set_type or card.name == "Harley Quin":
            raise InvalididDetectiveSet("Not a valid detective set. Learn the rules little cheater.")
        
        dset.cards.append(card)

        CardService(self._db).unrelate_card_player(card.id, player.id)

        if set_type == DetectiveSetType.SIBLINGS_BERESFORD:
            dset.type = DetectiveSetType.SIBLINGS_BERESFORD
        
        cancelable = True
        
        if dset.type == DetectiveSetType.SIBLINGS_BERESFORD:
            cancelable = False

        event = self._event_managaer.create(

            type=EventType.PLAY_DETECTIVE,
            game=game,
            main_player=player,
            selected_player=dset.player,
            played_card=card,
            dset=dset,
            cancelable=cancelable
        )

        if cancelable:
            game.action_status = ActionStatus.UNBLOCKED

            for p in game.players:
                p.turn_action = TurnAction.PLAY_NSF


        self._db.flush()
        self._db.commit()

        return event
      
    def select_own_card(self, game: Game, player_id: int, card_id: int) -> tuple[bool, EventType, Card | None, Card | None, Player | None, Player | None]:
        from App.events.services import EventManager
        player = self._db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        if player.turn_action != TurnAction.CARD_TRADE and player.turn_action != TurnAction.DEAD_CARD_FOLLY:
            raise NotPlayersTurnError(f"Player {player_id} cannot select own card now")
        
        card = next((card for card in player.cards if card.id == card_id))
        if not card:
            raise NotCardInHand(f"Card {card_id} not found in player's hand")
        
        actionResolved = False
        main_player = None
        selected_player = None
        main_player_card = None
        selected_player_card = None

        if player.turn_action == TurnAction.DEAD_CARD_FOLLY:
            event_type = EventType.DEAD_CARD_FOLLY
        else:
            event_type = EventType.CARD_TRADE

        event = EventManager(self._db).create(
            type=event_type,
            game=game,
            main_player=player,
            played_card=card,
            resolved=False,
        )

        self._db.flush()
        self._db.commit()
        
        related_events = EventManager(self._db).get_unresolved_events_by_event_type(game.id, event_type)

        if event_type == EventType.CARD_TRADE and len(related_events) == 2:
            main_player, selected_player, main_player_card, selected_player_card = self.resolver_card_trade(related_events)
            actionResolved = True
        elif event_type == EventType.DEAD_CARD_FOLLY and len(related_events) == len(game.players):
            self.resolver_dead_card_folly(game, related_events)
            actionResolved = True

        return actionResolved, event_type, main_player_card, selected_player_card, main_player, selected_player
    
    def resolver_card_trade(self, event: list[GameEvent]):
        players = [e.main_player for e in event]
        main_player = next(p for p in players if p.turn_status == TurnStatus.TAKING_ACTION)
        selected_player = next(p for p in players if p.turn_status != TurnStatus.TAKING_ACTION)

        player1 = event[0].main_player
        card1 = event[0].played_card
        player2 = event[1].main_player
        card2 = event[1].played_card
            
        main_player_card = next(card for card in main_player.cards if (card.id == card1.id) or (card.id == card2.id))
        selected_player_card = next(card for card in selected_player.cards if (card.id == card1.id) or (card.id == card2.id))

        self._card_service.unrelate_card_player(card1.id, player1.id)
        self._card_service.unrelate_card_player(card2.id, player2.id)
        self._card_service.relate_card_player(player1.id, card2.id)
        self._card_service.relate_card_player(player2.id, card1.id)
        event[0].resolved = True
        event[1].resolved = True

        main_player.turn_status = TurnStatus.DISCARDING_OPT
        main_player.turn_action = TurnAction.NO_ACTION
        selected_player.turn_action = TurnAction.NO_ACTION
        
        self._db.flush()
        self._db.commit()

        return main_player, selected_player, main_player_card, selected_player_card

    def resolver_dead_card_folly(self, game: Game, events: list[GameEvent]):

        eventDirection = next (e for e in game.events if e.type == EventType.DEAD_CARD_FOLLY_DIRECTION and not e.resolved)

        direction = eventDirection.direction
        players = sort_players(game.players)

        if direction == Direction.CLOCKWISE:
            for i in range (len(players)):
                current_player = players[i]
                next_player = players[(i + 1) % len(players)]
                card = next (e for e in events if e.main_player.id == current_player.id).played_card
                self._card_service.unrelate_card_player(card.id, current_player.id)
                self._card_service.relate_card_player(next_player.id, card.id)
                current_player.turn_action = TurnAction.NO_ACTION
                if current_player.turn_status == TurnStatus.TAKING_ACTION:
                    players[i].turn_status = TurnStatus.DISCARDING_OPT

        elif direction == Direction.COUNTERCLOCKWISE:
            for i in range (len(players)):
                current_player = players[i]
                previous_player = players[(i - 1) % len(players)]
                card = next (e for e in events if e.main_player.id == current_player.id).played_card
                self._card_service.unrelate_card_player(card.id, current_player.id)
                self._card_service.relate_card_player(previous_player.id, card.id)
                current_player.turn_action = TurnAction.NO_ACTION
                if current_player.turn_status == TurnStatus.TAKING_ACTION:
                    players[i].turn_status = TurnStatus.DISCARDING_OPT

        eventDirection.resolved = True
        for event in events:
            event.resolved = True

        self._db.flush()
        self._db.commit()
