from App.events.resolvers.base_resolver import BaseEventResolver
from App.players.enums import PlayerRole, TurnAction, TurnStatus
from App.card.services import CardService
from App.decks.discard_deck_service import DiscardDeckService
from App.exceptions import DeckNotFoundError, GameNotFoundError, NotPlayersTurnError, PlayerNotFoundError, SecretNotFoundError, SecretNotRevealed
from App.games.enums import GameStatus, Winners
from App.games.models import Game
from App.games.services import GameService
from App.players.models import Player
from App.players.services import PlayerService
from App.secret.enums import SecretType
from App.secret.services import relate_secret_player, unrelate_secret_player


class CardsOffTheTableResolver(BaseEventResolver):
    
    def resolve(self):
        game = self.event.game
        player = self.event.main_player
        card = self.event.played_card

        turn_action = CardService(self._db).select_event_type(game, player, card)
        if turn_action in [TurnAction.NO_ACTION, TurnAction.NO_EFFECT]:
            player.turn_status = TurnStatus.DISCARDING_OPT
        else:
            player.turn_status = TurnStatus.TAKING_ACTION
            player.turn_action = turn_action

        self._db.flush()
        self._db.commit()

        return turn_action
    
    
    
class AnotherVictimResolver(BaseEventResolver):
    
    def resolve(self):
        game = self.event.game
        player = self.event.main_player
        card = self.event.played_card

        turn_action = CardService(self._db).select_event_type(game, player, card)
        if turn_action in [TurnAction.NO_ACTION, TurnAction.NO_EFFECT]:
            player.turn_status = TurnStatus.DISCARDING_OPT
        else:
            player.turn_status = TurnStatus.TAKING_ACTION
            player.turn_action = turn_action

        self._db.flush()
        self._db.commit()

        return turn_action


class LookIntoTheAshesResolver(BaseEventResolver):
    
    def resolve(self):
        game = self.event.game
        player = self.event.main_player
        card = self.event.played_card

        turn_action = CardService(self._db).select_event_type(game, player, card)
        if turn_action in [TurnAction.NO_ACTION, TurnAction.NO_EFFECT]:
            player.turn_status = TurnStatus.DISCARDING_OPT
        else:
            player.turn_status = TurnStatus.TAKING_ACTION
            player.turn_action = turn_action

        self._db.flush()
        self._db.commit()

        top_cards = self.get_top_five_discarded_cards(player, game.id)
        return turn_action, top_cards
    
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
    
    


class AndThereWasOneMoreResolver(BaseEventResolver):
    
    def resolve(self):
        game = self.event.game
        player = self.event.main_player
        card = self.event.played_card

        turn_action = CardService(self._db).select_event_type(game, player, card)
        if turn_action in [TurnAction.NO_ACTION, TurnAction.NO_EFFECT]:
            player.turn_status = TurnStatus.DISCARDING_OPT
        else:
            player.turn_status = TurnStatus.TAKING_ACTION
            player.turn_action = turn_action

        self._db.flush()
        self._db.commit()

        return turn_action
    
    

class DelayTheMurderersEscapeResolver(BaseEventResolver):
    
    def resolve(self):
        game = self.event.game
        player = self.event.main_player
        card = self.event.played_card

        turn_action = CardService(self._db).select_event_type(game, player, card)
        if turn_action in [TurnAction.NO_ACTION, TurnAction.NO_EFFECT]:
            player.turn_status = TurnStatus.DISCARDING_OPT
        else:
            player.turn_status = TurnStatus.TAKING_ACTION
            player.turn_action = turn_action

        self._db.flush()
        self._db.commit()

        top_cards = self.get_top_five_discarded_cards(player, game.id)
        return turn_action, top_cards
    
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
    
    

class EarlyTrainToPaddingtonResolver(BaseEventResolver):

    def resolve(self):
        game = self.event.game
        player = self.event.main_player
        card = self.event.played_card

        turn_action = CardService(self._db).select_event_type(game, player, card)
        if turn_action in [TurnAction.NO_ACTION, TurnAction.NO_EFFECT]:
            player.turn_status = TurnStatus.DISCARDING_OPT
        else:
            player.turn_status = TurnStatus.TAKING_ACTION
            player.turn_action = turn_action

        self._db.flush()
        self._db.commit()

        self.early_train_to_paddington(game, player)
        return turn_action
    
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
                DiscardDeckService(self._db).relate_card_to_discard_deck(discard_deck.id, card)
                
        else:
            while rep_deck.number_of_cards > 0:
                card = max(rep_deck.cards, key=lambda c: c.order)
                CardService(self._db).unrelate_card_reposition_deck(rep_deck.id, card.id)
                DiscardDeckService(self._db).relate_card_to_discard_deck(discard_deck.id, card)

        self.end_game(game.id)

        player.turn_status = TurnStatus.DISCARDING_OPT
        player.turn_action = TurnAction.NO_ACTION

        self._db.flush()
        self._db.commit()

    def end_game(self, game_id: int) -> Game:
        game: Game | None = GameService(self._db).get_by_id(game_id)
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


