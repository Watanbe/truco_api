from models.card import Card

class Player:
    """
    Representa um jogador em um jogo de cartas.

    A classe `Player` contém informações sobre o jogador, incluindo seu ID, nome e as cartas em sua mão.
    """
    
    def __init__(self, id: int, name: str, sid: str, cards: list[Card] = []):
        self.id = id
        self.name = name
        self.sid = sid
        self.cards = cards

    def throw_card_using_code(self, card_code: str) -> Card:
        """
        Remove uma carta da mão do jogador com base em seu código.
        :param card_code: Uma string representando o código da carta a ser removida da mão do jogador.
        :return: Um objeto da classe 'Card' que foi removido da mão do jogador, ou None se a carta não for encontrada.
        """
        for index, card in enumerate(self.cards):
            if card.code == card_code.upper():
                return self.cards.pop(index)
        return None
    
    def throw_card(self, card: Card) -> Card:
        """
        Remove uma carta da mão do jogador com base em um objeto 'Card'.
        :param card: Um objeto da classe 'Card' a ser removido da mão do jogador.
        :return: O objeto 'Card' que foi removido da mão do jogador.
        """
        return self.throw_card_using_code(card.code)

    # Essa função provavelmente vai sair daqui.
    def increase_hand_value(self) -> None:
        pass

    def to_json(self):
        """
        Converte os atributos do jogador em um dicionário JSON.
        :return: Um dicionário com as informações do jogador.
        """
        return {
            'id': self.id,
            'name': self.name,
            'cards': self.cards_to_json()
        }

    def cards_to_json(self) -> dict:
        return {
            'cards': [card.to_json() for card in self.cards]
        }    