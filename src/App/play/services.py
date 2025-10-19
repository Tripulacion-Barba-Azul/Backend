from sqlalchemy.orm import Session

from App.card.services import CardService
from App.decks.discard_deck_service import DiscardDeckService
from App.card.services import CardService
from App.decks.draft_deck_service import DraftDeckService
from App.exceptions import (
    GameNotFoundError,
    InSocialDisgraceException,
    InvalididDetectiveSet,
    NotCardInHand,
    NotPlayableCard,
    NotPlayersTurnError,
    ObligatoryDiscardError,
    PlayerNeedSixCardsError,
    PlayerNotFoundError,
    PlayerHave6CardsError,
    DeckNotFoundError,
    SecretAlreadyRevealedError,
    SecretNotFoundError,
    SecretNotRevealed)
from App.games.models import Game
from App.games.services import GameService
from App.games.enums import GameStatus, Winners
from App.secret.enums import SecretType
from App.secret.services import get_secret, relate_secret_player, reveal_secret, unrelate_secret_player
from App.players.models import Player
from App.players.enums import PlayerRole, TurnAction, TurnStatus
from App.players.services import PlayerService
from App.sets.services import DetectiveSetService
from App.card.models import Card, Event

class PlayService:

    def __init__(self, db: Session):
        self._db = db
        self._game_service = GameService(db)
        self._player_service = PlayerService(db)
        self._card_service = CardService(db)
        self._discard_deck_service = DiscardDeckService(db)
        self._detective_set_service = DetectiveSetService(db)

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
        if not isinstance(card, Event):
            raise NotPlayableCard("You tried to play a card that is not playable.")
        
        self._card_service.unrelate_card_player(card_id, player_id)
        if card.name != "Early Train to Paddington" and card.name != "Delay the Muderer's Escape":
            self._discard_deck_service.relate_card_to_discard_deck(game.discard_deck.id, card)
        event = self._card_service.select_event_type(game, player, card)
        if event in [TurnAction.NO_ACTION, TurnAction.NO_EFFECT]:
            player.turn_status = TurnStatus.DISCARDING_OPT
        else:
            player.turn_status = TurnStatus.TAKING_ACTION
            player.turn_action = event

        self._db.flush()
        self._db.commit()

        return card, event

    def play_set(self, game, player_id, card_ids):
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
        
        event = self._detective_set_service.select_event_type(game, set_type)
        
        if event == TurnAction.NO_EFFECT:
            player.turn_action = TurnAction.NO_ACTION
            player.turn_status = TurnStatus.DISCARDING_OPT
        else :
            player.turn_action = event
            player.turn_status = TurnStatus.TAKING_ACTION


        self._db.flush()
        self._db.commit()

        return new_set

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

        for card_id in cards_id:
            card = self._card_service.get_card(card_id)
            card = self._player_service.discard_card(player_id, card)
            discarded_cards.append(card)
            if card.name != "Early Train to Paddington":
                self._discard_deck_service.relate_card_to_discard_deck(game.discard_deck.id, card)
            else:
                self.early_train_to_paddington(game, player)

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
        if len(player.cards) != 6:
            raise PlayerNeedSixCardsError(f"Player {player_id} needs to have six cards to end turn")
        
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
        
        if player.turn_status != TurnStatus.TAKING_ACTION:
            raise NotPlayersTurnError(f"Player {player_id} cannot select any player now")
        
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

        countNotSoFast = None
        if event == TurnAction.CARDS_OFF_THE_TABLE:
            countNotSoFast = self.cards_off_the_tables(game, player, selected_player)

        elif event == TurnAction.SELECT_ANY_PLAYER:
                player.turn_action = TurnAction.NO_ACTION
                selected_player.turn_action = TurnAction.REVEAL_OWN_SECRET

        elif event == TurnAction.SATTERWAITEWILD:
            player.turn_action = TurnAction.NO_ACTION
            selected_player.turn_action = TurnAction.GIVE_SECRET_AWAY

        self._db.flush()
        self._db.commit()

        return game, player, selected_player, event, countNotSoFast

    def cards_off_the_tables(self, game: Game, player: Player, selected_player: Player) -> int:
        countNotSoFast = 0

        cards_player = list(selected_player.cards)
        for card in cards_player:
            if card.name == "Not so Fast!":
                card = self._player_service.discard_card(selected_player.id, card)
                self._discard_deck_service.relate_card_to_discard_deck(game.discard_deck.id, card)
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

    def reveal_secret_service(self, player_id: int, secret_id: int, revealed_player_id: int):

        player = self._db.query(Player).filter(Player.id == player_id).first()
        revealed_player = self._db.query(Player).filter(Player.id == revealed_player_id).first()

        if not player:
            raise PlayerNotFoundError(f"Player {player_id} not found")
        
        if not revealed_player:
            raise PlayerNotFoundError(f"Player {revealed_player_id} not found")

        if player.turn_status != TurnStatus.TAKING_ACTION:
            raise NotPlayersTurnError(f"It's not the turn of player {player_id}")

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
        player.turn_status = TurnStatus.DISCARDING_OPT
        player.turn_action = TurnAction.NO_ACTION

        self._db.commit()
        self._db.refresh(player)
        self._db.refresh(secret)
        self._db.refresh(revealed_player)

        return secret

    def hide_secret(self, player_id, secret_id, affected_player_id):

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
        player.turn_status = TurnStatus.DISCARDING_OPT
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
        self._player_service.set_social_disgrace(stolen_player)
        relate_secret_player(selected_player, secret, self._db)
        self._player_service.set_social_disgrace(selected_player)
        
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
    
    def get_top_five_discarded_cards(self, game_id):
        game = self._db.query(Game).filter_by(id=game_id).first()
        
        if not game:
            raise GameNotFoundError(f"No game found {game_id}")
        
        discard_deck = game.discard_deck
        if not discard_deck:
            raise DeckNotFoundError(f"Game {game_id} does not have a discard deck")
        
        sorted_cards = sorted(discard_deck.cards, key=lambda c: c.order, reverse=True)
        top_five_cards = sorted_cards[:6]
        if top_five_cards:
            top_five_cards.pop(0)
        
        return top_five_cards
    
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
        for p in game.players:
                if p.turn_status == TurnStatus.TAKING_ACTION:
                    current_turn_player = p
        if not current_turn_player:
                raise PlayerNotFoundError(f"Player not found")

        secret.revealed = True
        self._db.flush()
        self._db.commit()

        event = player.turn_action
        if event is TurnAction.GIVE_SECRET_AWAY:
            unrelate_secret_player(player, secret, self._db)
            relate_secret_player(current_turn_player, secret, self._db)
            secret.revealed = False

        # TODO: ACA HAY CASO DESGRACIA SOCIAL
        self._player_service.set_social_disgrace(player)
        current_turn_player.turn_status = TurnStatus.DISCARDING_OPT
        player.turn_action = TurnAction.NO_ACTION

        self._db.flush()
        self._db.commit()

        return event, current_turn_player, secret, player

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

