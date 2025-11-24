
from src.App.card.services import CardService
from src.App.decks.discard_deck_service import DiscardDeckService
from src.App.events.resolvers.base_resolver import BaseEventResolver
from src.App.exceptions import GameNotFoundError, NotPlayersTurnError
from src.App.games.enums import GameStatus, Winners
from src.App.games.models import Game
from src.App.games.services import GameService
from src.App.players.enums import PlayerRole, TurnAction, TurnStatus
from src.App.players.models import Player
from src.App.secret.enums import SecretType


class DiscardETTPResolver(BaseEventResolver):
    def resolve(self):
        game = self.event.game
        player = self.event.main_player

        self.early_train_to_paddington(game, player)
        player.turn_status = TurnStatus.DRAWING

    def early_train_to_paddington(self, game: Game, player: Player):
            
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
