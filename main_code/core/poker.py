import random
from collections import defaultdict
from copy import deepcopy
from abc import ABC
from core.winner import get_winner, all_hands_ranked, group_rank_pre
from core.core_lib import *

# TODO test valid bets on raises
# TODO make calling range capped and raising range tighter with percentages
# TODO Consider hand within all hands (not just range)
# TODO test get_ps_strength
# TODO bots dont bet thinly enough post flop
# TODO consider draws
# TODO tighten opening range
# TODO change range depending on position and num of players
# TODO hold invested of each player? currently inefficient replace the functions
# TODO if big bet and 1 player calls, bb will also call
# TODO consider hand strength with betsize
# 3bet more oop
# underbluffs?
# Use mdf or pot odds


class PokerPlayer(ABC):
    pos_i_names = {
        0: "Button",
        1: "Small blind",
        2: "Big blind",
        3: "UTG",
        4: "Hijack",
        5: "Cutoff",
    }

    def __init__(self, table, id=0, chips=1000):
        self.chips = chips
        self.table = table
        self.id = id
        self.round_invested = 0
        self.inactive = False
        self.action = None
        self.hole_cards = None
        self.position_name = ""
        self.fold = True
        self.bet_count_on_action = 0

        while self.id == 0 or self.id in table.ids:
            self.id = random.randint(1000, 9999)

    def __eq__(self, other):
        if not isinstance(other, PokerPlayer):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def set_pos_names(self, players):
        self.pos_names = {}
        for i, pos in enumerate(
            [
                *[
                    "UTG" + (f" +{n}" if n != 0 else "")
                    for n in range(max(players - 5, 0))
                ],
                "Lojack",
                "Hijack",
                "Cutoff",
                "Button",
                "Small blind",
                "Big blind",
            ][-players:]
        ):
            self.pos_names[i + 1] = pos

    def new_hand(self, i):

        self.fold = False
        self.agg = False
        if self.chips <= 0:
            self.fold = True

        a_player_count = len(self.table.active_players)
        self.position_i = ((i - self.table.sb_i) % a_player_count + 1) % a_player_count
        self.position_name = PokerPlayer.pos_i_names[self.position_i]
        self.hole_cards = self.table.deck[self.position_i * 2 : self.position_i * 2 + 2]

        if a_player_count == 2:  # heads up
            self.total_invested = min(self.table.blinds[self.position_i], self.chips)
        elif self.position_i in [1, 2]:  # One of the blinds maybe change to name
            self.total_invested = min(
                self.table.blinds[self.position_i - 1], self.chips
            )
        else:
            self.total_invested = 0

        self.round_invested = self.extra = self.total_invested
        self.chips -= self.round_invested
        self.all_in = not (bool(self.chips) or self.fold)

    def start_round(self, start=False):
        if not start:
            # for the blinds
            self.round_invested = 0
        self.action = self.action_text = None
        self.extra = self.bet_count_on_action = 0
        self.invalid_raise = False

    def set_inactive(self):
        self.position_name = ""
        self.inactive = True

    def _apply_action(self, roundTotal):
        """Updates values depending on self.action and and self.round_invested"""

        self.bet_count_on_action = self.table.bet_count

        if self.action == 1:
            # self.action_text is only for debugging
            self.action_text = "folds"
            self.fold = True
            self.agg = False
            self.extra = 0

        elif self.action == 2:

            self.agg = False
            self.extra = roundTotal - self.round_invested
            self.action_text = "calls" if self.extra else "checks"

            if roundTotal >= self.round_invested + self.chips:
                self.all_in = True
                self.extra = self.chips

        else:

            self.bet_count_on_action += 1
            self.action_text = f"bets {self.extra}"

            self.agg = True

            self.invalid_raise = (
                self.round_invested + self.extra
                < self.table.last_bet + self.table.min_increase
            )

        self.round_invested += self.extra
        self.total_invested += self.extra
        self.chips -= self.extra

        if self.chips == 0:
            self.all_in = True

    def is_valid(self, table, action_info) -> bool:
        """Returns if an action is valid"""

        print(action_info)
        action, extra = action_info[0], action_info[1] - self.round_invested  # CHANGE

        if isinstance(self, Human):
            if table.community:
                end = f", Community Cards {table.community}"
            else:
                end = ""

            print(f"\n User cards are {self.hole_cards}{end}")
        else:
            print(f"\n {self.position_name} cards are {self.hole_cards}")

        if action == 3:
            print(
                self.round_invested,
                action_info,
                table.last_bet,
                table.min_increase,
                self.chips,
            )

            if (
                (
                    self.round_invested + extra < table.last_bet + table.min_increase
                    and extra < self.chips
                )
                or extra > self.chips
                or table.only_call == True
                or self.round_invested + extra < table.last_bet
            ):
                print("invalid")
                return False

        return True

    def move(self, table, action_info) -> bool:
        """Call with table and action_info
        This method will call all other required methods to
        apply action. Will return if action was valid"""
        valid = self.is_valid(table, action_info)

        if not valid and isinstance(self, Bot):
            print(
                table.last_bet,
                action_info,
                self.round_invested,
                self.chips,
                self.can_only_call(),
                self.table.r,
            )
            raise Exception
        elif not valid:
            return False

        self.action, self.extra = (
            action_info[0],
            action_info[1] - self.round_invested,
        )
        self._apply_action(table.last_bet)

        # TODO
        name = "(USER)" if isinstance(self, Human) else "(BOT)"
        print(
            f"\n {self.position_name} {name} {self.action_text} with {self.chips} chips behind {self.round_invested} invested this round"
        )

        return True

    def add_chips(self, extra):
        self.chips += extra

    def get_pot(self):
        """Returns the total chips the player can win in the current pot"""
        count = 0
        pot_sum = 0
        for p in self.table.pot:
            count += p[0]
            if count > self.chips + self.total_invested:
                rem_chips = self.chips + self.total_invested - count + p[0]
                pot_sum += sum([min(rem_chips, x) for x in p[2].values()])
                return pot_sum
            pot_sum += sum(p[2].values())
        return pot_sum

    def get_round_total(self):
        return min(self.table.last_bet, self.chips + self.round_invested)


class Human(PokerPlayer):
    pass


class Bot(PokerPlayer, ABC):
    def can_only_call(self) -> bool:
        return (
            self.table.last_bet >= self.round_invested + self.chips
            or self.table.only_call == True
        )


class RandomBot(Bot):
    def _get_bet(self, table):
        print("bets", table.last_bet)

        try:
            extra = random.randint(
                min(
                    self.chips + self.round_invested,
                    table.last_bet + table.min_increase,
                ),  # changed
                min(
                    max(
                        table.last_bet * 2 + table.min_increase,
                        int(table.get_pot() * 2.5),
                    ),
                    self.chips + self.round_invested,
                ),
            )

            if extra < 0:
                raise Exception

        except:
            print("ERROR", self.chips, self.round_invested, table.last_bet, table.pot)
            print(
                min(self.chips, table.last_bet - self.round_invested + table.last_bet),
                min(int(table.get_pot() * 2.5), self.chips),
            )
            raise Exception

        return extra

    def get_action(self, table):

        round_total = table.last_bet
        l = 1
        h = 3
        if round_total == self.round_invested:
            l = 2
        if self.can_only_call():
            h = 2

        action = random.randint(l, h)

        if action == 3:
            bet = self._get_bet(table)
        else:
            bet = 0

        # return 2, 0
        # return 3, self.chips
        return action, bet


class BotV1(Bot):
    def __init__(self, table, id=0, chips=1000):
        super().__init__(table, id=id, chips=chips)
        self._MDFC = 1
        self._RMDFC = 1.3

    def new_hand(self, i):
        self._current_range = None
        return super().new_hand(i)

    def get_action(self, table):
        self.to_call = min(
            table.last_bet - self.round_invested, self.chips
        )  # make function

        if table.r == 0:
            action = self.pre_flop(table)
            self._set_pre_range(action)
        else:
            action = self.post_flop(table)

        # return 2, 0
        return action

    def pre_flop(self, table) -> tuple[int, int]:
        """Returns the action if it is currently the pre_flop"""

        self.set_pre_var(table)

        r = random.randint(1, 10)

        print(
            "max_chips",
            self.round_total,
            self.max_chips,
            self.min_call,
            self.max_call,
            # pot_odds,
            self.to_call,
            table.curr_player_i == table.last_agg_i,
            (table.curr_player_i + 1) % table.no_players,
            table.last_agg_i,
            r,
            table.still_to_act(),
            table.last_bet,
            self.get_pot(),
        )

        if self.max_call != True and (
            (self.round_total < self.max_chips / 2 and r >= 2)
            or (self.min_call and (r >= 10 or table.last_bet == 20))
        ):
            return 3, self._get_bet(table)
        elif self.min_call:
            return 2, 0
        return 1, 0

    def set_pre_var(self, table):
        """Sets variables required to determine action for pre-flop"""
        self.round_total = self.get_round_total()
        self.pot_odds = self.calc_po(frac=True)

        c1, c2 = self.hole_cards

        i1, i2 = strength_index(c1, c2)

        strength = strengths[i1][i2]
        self.max_chips = strength**3 * 3 * table.blinds[-1]
        self.min_call = self.round_total < self.max_chips
        self.max_call = False
        if self.min_call == False and (self.to_call == 0 or self.valid_pre_po()):
            self.min_call = self.max_call = True
        self.max_call = self.max_call or self.can_only_call()

    def _pre_flop_bet(self, table):
        if table.to_bb(table.last_bet) <= 3 or table.still_to_act == 0:
            print("in bb", table.to_bb(table.last_bet))

            return (
                table.last_bet * 3
                + sum(
                    table.blinds[-1]
                    for p in table.active_players
                    if p.round_invested == 20
                )
                - table.blinds[-1]
            )  # for bb

        return table.last_bet * 2

    def _set_pre_range(self, action):
        """Sets range for pre-flop"""
        if action == 1:
            self._current_range = None
            return
        flag = action == 3
        self.pre_calling_range(flag)

    def pre_raising_range(self):  # TODO
        """Sets pre_flop raising range"""
        if self.table.last_bet == 20:
            self.pre_calling_range(flag=True)
        else:
            min_strength = (self.round_total * 2 / self.table.blinds[-1] / 3) ** (1 / 3)

            self.update_range(min_strength=min_strength)

    def pre_calling_range(self, flag=False):
        """Sets pre flop folding range"""
        if self.valid_pre_po() or self.to_call == 0 and not flag:
            min_strength = 0
            if self._current_range != None:
                return
        else:
            min_strength = (self.round_total / self.table.blinds[-1] / 3) ** (1 / 3)
            # max_strength = (self.round_total * 2 / self.table.blinds[-1] / 3) ** (1 / 3)

        self.update_range(min_strength=min_strength)

    def _get_bet(self, table):
        print("bets", table.last_bet)

        if table.r == 0:
            return min(
                self._pre_flop_bet(table), self.chips + self.round_invested
            )  # changed
        try:
            extra = random.randint(
                min(
                    self.chips + self.round_invested,
                    table.last_bet + table.min_increase,
                ),  # changed
                min(
                    max(
                        table.last_bet * 2 + table.min_increase,
                        int(table.get_pot() * 2.5),
                    ),
                    self.chips + self.round_invested,
                ),
            )

            if extra < 0:
                raise Exception

        except:
            print("ERROR", self.chips, self.round_invested, table.last_bet, table.pot)
            print(
                min(self.chips, table.last_bet - self.round_invested + table.last_bet),
                min(int(table.get_pot() * 2.5), self.chips),
            )
            raise Exception

        return extra

    def valid_pre_po(self):
        return (
            self.pot_odds > 3
            and self.table.still_to_act() == 0
            and len([p for p in self.table.active_players if not p.fold])
        )

    def update_range(self, hands=None, min_strength=-1, max_strength=float("inf")):
        """Updates range with given minimum and maximum strength"""
        if hands == None:
            hands = sorted_hands
        self._current_range = group_rank_pre(
            sorted_hands[
                strengths_to_index[get_ps_strength(max_strength, minimum=False)][
                    0
                ] : strengths_to_index[get_ps_strength(min_strength)][-1]
                + 1
            ],
        )

    def post_flop(self, table):
        """Returns action for post flop"""
        self._current_range = all_hands_ranked(
            table.community, p_hands=self._current_range.keys()
        )
        min_rank = len(self._current_range) * self.calc_mdf()

        try:
            rank = self._current_range[sort_hole(*self.hole_cards)]
        except:
            print(self._current_range)
            rank = self._current_range[sort_hole(*self.hole_cards)]
            raise Exception

        action = None
        if rank > min_rank and self.to_call > 0:
            return (1, 0)
        elif self.can_only_call() or rank > min_rank / 3:
            action = (2, 0)
        else:
            action = (3, self._get_bet(table))

            min_rank *= (
                self.calc_mdf(applied=False, bet=action[1] - table.last_bet)
                * self._RMDFC
            )

            print(self.calc_mdf(applied=False, bet=action[1] - table.last_bet))

        self._current_range = all_hands_ranked(
            table.community,
            p_hands=[h for h, r in self._current_range.items() if r <= min_rank],
        )

        print(rank, len(self._current_range), action)

        if rank > len(self._current_range):
            self._current_range[sort_hole(*self.hole_cards)] = (
                len(self._current_range) + 1
            )
        return action

    def calc_mdf(self, applied=True, bet=None):
        """Calculate minimum defense frequency"""
        return (
            (self.get_pot() - self.to_call) / self.get_pot()
            if applied
            else self.get_pot() / (self.get_pot() + bet)
        )

    def calc_po(self, frac=False):
        """Calculate pot odds"""
        po = (self.to_call) / (self.get_pot() + self.to_call)
        return po if frac == False else po**-1 if po != 0 else float("inf")


class Table:
    # deck = ['🂱', '🂲', '🂳', '🂴', '🂵', '🂶', '🂷', '🂸', '🂹', '🂺', '🂻', '🂼', '🂽', '🂾', '🂡', '🂢', '��', '🂤', '🂥', '🂦', '🂧', '🂨', '🂩', '🂪', '🂫', '🂬', '🂭', '🂮', '🃁', '🃂', '🃃', '🃄', '🃅', '🃆', '🃇', '🃈', '🃉', '🃊', '🃋', '🃌', '🃍','🃑', '🃒', '🃓', '🃔', '🃕', '🃖', '🃗', '🃘', '🃙', '🃚', '🃛', '🃜', '🃝', '🃞']

    def __init__(self) -> None:
        self.players = [None] * 6
        self.active_players = []
        self.deck = deck
        self.blinds = [10, 20]
        self.sb_i = 0
        self.running = False
        self.community = []
        self.correct_total_chips = 0
        self.r = 0
        self.pot = [[0, False, {}]]
        self.ids = []
        self.current_player = -1

    def add_new_player(self, chips=2500):
        return self.add_player(Human(self, chips=chips))

    def add_player(self, new_player: PokerPlayer) -> int | None:
        if None not in self.players:
            return

        for i, p in enumerate(self.players):
            if p == None:
                self.players[i] = new_player
                break

        self.ids.append(new_player.id)
        self.correct_total_chips += new_player.chips

        return i

    def remove_player(self, i: int):
        # TODO test
        # potential BUG where player leaves during all in and results in chips disappearing
        player = self.players[i]

        # This is a fallback incase the player to be removed
        # Is the next player to act
        if player == self.current_player:
            self.full_single_move((1, 0))
        else:
            player.fold = True
            self.players_remaining -= 1
            self.active_in_hand -= 1
            self.set_skip_r()

        self.players[i] = None
        self.ids.remove(player.id)
        self.correct_total_chips -= player.chips

    def can_move(self):
        """Returns if the current player can make a move"""
        return (
            self.current_player.all_in == False
            and self.current_player.fold == False
            and self.r < self.skip_round
        )

    def next_player(self, c=None):
        if c == None:
            c = self.curr_player_i
        return (c + 1) % self.no_players

    def poss_end_hand(self) -> bool | None:
        """Checks if there is only 1 player remaining
        and if so, ends the hand and returns True"""
        if self.players_remaining == 1:
            self.end_hand()
            return True

    def full_single_move(self, action_info: tuple[int, int | float]):
        """Validates and executes a user action
        Automatically ends the round
        Should not be used if state needs to be emitted before round ends"""
        end_valid = self.single_move(action_info)

        if end_valid:
            self.start_round()

    def single_move(self, action_info: tuple[int, int | float]):
        """Returns None if the move was invalid else True if the round ends else False.

        Checks if the action is valid, and if the current player can make an action.
        If valid, executes the action

        If so, calls and returns Table.end_move() to finish the action
        Will not end the round automatically (to give state a chance to be returned)
        """
        print("player remaining", self.players_remaining)

        valid = self.current_player.move(self, action_info)

        if not (self.running and valid):  # TODO decide if to return something better
            print("not valid", action_info)
            return

        if self.current_player.fold == True:
            self.players_remaining -= 1

        if self.current_player.fold or self.current_player.all_in:
            self.active_in_hand -= 1

            self.set_skip_r()
            # if self.active_in_hand == 1:
            #     self.skip_round = self.r + 1

        print("pre", self.pot, "\n")
        self.set_pot()
        print("pot", self.pot)
        return self.end_move()

    def end_move(self):
        """Returns True if a betting round has finished else False

        Updates attributes (last_agg_i, min_raise, current_player ...)"""
        if self.running == False or self.poss_end_hand() == True:
            return False

        if self.current_player.agg:
            # The index of the player at which players can only call
            self.only_call_i: int = (
                self.last_agg_i if self.current_player.invalid_raise else -1
            )
            self.last_agg_i: int = self.curr_player_i

            if not self.current_player.invalid_raise:
                self.min_increase = self.current_player.round_invested - self.last_bet
                print("invalid raise")

            self.last_bet = self.current_player.round_invested
            print(self.min_increase)

        if self.current_player.action == 3:
            self.bet_count += 1

        self.current_player.agg = False
        self.curr_player_i = self.next_player()
        self.current_player = self.active_players[self.curr_player_i]
        self.current_player.agg = False

        if self.last_agg_i == self.curr_player_i:
            return True
        if self.only_call_i == self.curr_player_i:
            self.only_call = True

        return False

    def start_round(self, first=False):
        """Should be called if Table.end_move() returns True

        Changes attributes and calls necessary methods to start a betting round"""
        if not first:
            self.r += 1

        for p in self.active_players:
            p.start_round(first)

        if self.r == 4:
            self.end_hand()
            return

        name = {0: "Pre Flop", 1: "Flop", 2: "Turn", 3: "River"}

        self.min_increase = self.blinds[-1]
        self.only_call = False
        self.only_call_i = -1
        if self.r == 0:
            self.curr_player_i = self.last_agg_i = (
                self.sb_i + (2 if self.no_players != 2 else 1)
            ) % self.no_players
            self.last_bet = self.blinds[-1]
            self.community = []
            self.bet_count = 1

        else:
            self.curr_player_i = self.last_agg_i = self.sb_i
            self.last_bet = 0
            self.community = self.deck[
                self.community_card_i : self.community_card_i + self.r + 2
            ]
            self.bet_count = 0

            print(f"\n{name[self.r]} Cards {self.community} pot {self.pot}")

        try:
            self.current_player = self.active_players[self.curr_player_i]
            print("b", self.r, self.current_player.position_i, self.curr_player_i)
        except:
            print(
                "aa",
                self.curr_player_i,
                self.active_players,
                self.sb_i,
                self.no_players,
            )
            raise Exception

    def set_pot(self, player=None):
        """Sets the pot. Must be called after each action"""
        if player == None:
            player = self.current_player

        if player.fold == False:
            remaining = player.extra
            new_pot = []
            end = False

            p_before = deepcopy(self.pot)
            for p in self.pot:

                if end:
                    raise Exception(p_before, "\n", p, end)

                single_investment, required, contents = p.copy()
                if remaining <= 0:  # no chips remaining (just keep it the same)
                    new_pot.append(p)
                    continue

                rem_after = remaining + contents[player] - single_investment

                if rem_after < 0:  # make it subtract from the current pot
                    remaining += contents[player]
                    new_contents = defaultdict(int)
                    for key, value in contents.items():
                        new_contents[key] = min(remaining, value)
                        contents[key] = max(0, value - remaining)

                    new_contents[player] = remaining
                    new_pot.append([remaining, player.all_in, new_contents])
                    new_pot.append([single_investment - remaining, required, contents])

                    remaining = 0

                elif rem_after == 0 or required:
                    contents[player] = single_investment
                    new_pot.append(
                        [single_investment, required or player.all_in, contents]
                    )
                    remaining = rem_after

                else:
                    # current pot is not re-added
                    if rem_after <= 0:
                        raise Exception(rem_after)
                    end = True

                    remaining = rem_after

                if remaining < 0:
                    raise Exception(self.pot, p, remaining)

            if remaining:

                if not end:
                    single_investment = 0
                    contents = defaultdict(int)

                contents[player] = single_investment + remaining
                new_pot.append([single_investment + remaining, player.all_in, contents])

            self.pot = new_pot

    def get_pot(self):
        return sum(sum(p[2].values()) for p in self.pot)

    def still_to_act(self):
        c = 0
        ci = self.next_player()
        while True:
            p = self.active_players[ci]
            if self.last_agg_i == ci or ci == self.curr_player_i:
                return c
            if not (p.fold or p.all_in):
                c += 1
            ci = self.next_player(ci)

    def start_hand(self):
        """Updates attributes (pot, position, etc) and takes blinds to start a hand"""
        self.running = True
        self.active_players = []
        button_bust = False

        for p in [x for x in self.players if x]:
            if p.chips:
                self.active_players.append(p)
                if p.inactive:
                    raise Exception(self.players, [x.chips for x in self.players])
            elif not p.inactive:
                p.set_inactive()
                # p.fold = True
                if p.position_i == 0:
                    button_bust = True

        self.no_players = len(self.active_players)

        if not button_bust:
            self.sb_i = self.sb_i + 1

        self.sb_i %= self.no_players
        # to_call, 1 or more players all in, each player invested in pot
        self.pot = [[0, False, defaultdict(int)]]

        # indexing from 0-3
        self.r = 0
        self.skip_round = float("inf")
        random.shuffle(self.deck)

        for i, p in enumerate(self.active_players):
            p.new_hand(i)

        for p in sorted(self.active_players, key=lambda x: x.total_invested)[-2:]:
            print("pre", self.pot, p.round_invested)
            self.set_pot(p)
            print("post", self.pot)

        print("pot", self.pot)

        self.active_in_hand = sum(
            [1 for p in self.active_players if not p.fold and not p.all_in]
        )
        self.players_remaining = sum([1 for p in self.active_players if not p.fold])
        self.community_card_i = self.no_players * 2

        self.start_round(first=True)

    def give_pot(self, pot):
        """Distributes a single (potentially side) pot to valid players"""
        c_players = [p for p, v in pot[2].items() if not p.fold and v == pot[0]]
        t_chips = sum(pot[2].values())
        if len(c_players) > 1:
            wInfo = get_winner([p.hole_cards for p in c_players], self.community)
        else:
            wInfo = [[None, 0]]

        print("winfo", wInfo)
        wHand = wInfo[0][0]
        wPIs = [x[1] for x in wInfo]
        winners = [p for i, p in enumerate(c_players) if i in wPIs]

        for i, w_p in enumerate(
            sorted(
                winners,
                key=lambda x: (x.position_i - 1) % (self.no_players + 1),
            )
        ):
            w_p.chips += t_chips // len(winners)
            if i < t_chips % len(winners):
                w_p.chips += 1
            print(w_p.chips)

        if wHand:
            end = f"with {wHand}"
        else:
            end = ""

        print([x.position_name for x in c_players])

        print(
            f"{'Winner' if len(winners) == 1 else 'Winners'} {', '.join([p.position_name for p in winners])} wins {pot} chips {end}"
        )

        print("Testing", [x.hole_cards for x in c_players], self.community)

    def end_hand(self):
        """Distributes chips to valid players"""
        print(self.r)
        self.running = False

        for i in range(len(self.pot) - 1, -1, -1):
            print(i)
            self.give_pot(self.pot[i])

        print(
            "total_chips",
            sum(p.chips for p in self.players if p),
            len([1 for x in self.players if x and x.chips]),
        )
        if sum(p.chips for p in self.players if p) != self.correct_total_chips:
            print("ERROR")

            #For pygbag
            raise Exception(
                [p.chips for p in self.players if p], self.correct_total_chips
            )

    def to_bb(self, chips):
        return chips / self.blinds[1]

    def set_skip_r(self):
        if self.active_in_hand == 1:
            self.skip_round = self.r + 1


def start():

    table1 = Table()

    table1.add_player(
        Human(
            table1,
            chips=4000,
        )
    )

    for r in range(5):  # change to testing
        if r <= 0:
            chips = 2000
            table1.add_player(BotV1(table1, chips=chips))

        else:
            chips = 2000
            table1.add_player(BotV1(table1, chips=chips))

    # table1.add_player(
    #     Human(
    #         table1,
    #         chips=3000,
    #     )
    # )

    return table1


def new_table():
    pass


def main():
    table1 = start()
    running = True
    while running:
        table1.start_hand()

        input("Click Enter for next hand: \n")


if __name__ == "__main__":
    main()
