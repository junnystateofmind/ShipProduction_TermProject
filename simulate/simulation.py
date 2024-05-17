import numpy as np
from itertools import permutations
from baseball import Hitter, Diamond

def simulate_at_bat(hitter):
    result = np.random.rand()
    if result < hitter.single_prob():
        return 'hit'
    elif result < hitter.single_prob() + hitter.double_prob():
        return 'double'
    elif result < hitter.single_prob() + hitter.double_prob() + hitter.triple_prob():
        return 'triple'
    elif result < hitter.single_prob() + hitter.double_prob() + hitter.triple_prob() + hitter.home_run_prob():
        return 'home_run'
    elif result < hitter.single_prob() + hitter.double_prob() + hitter.triple_prob() + hitter.home_run_prob() + hitter.bb_prob():
        return 'base_on_balls'
    elif result < hitter.single_prob() + hitter.double_prob() + hitter.triple_prob() + hitter.home_run_prob() + hitter.bb_prob() + hitter.hbp_prob():
        return 'hit_by_pitch'
    else:
        # 병살, 희플 등 로직 추가 구현 필요
        return 'out'

def simulate_game(lineup):
    diamond = Diamond()
    outs = 0
    current_batter_index = 0

    while outs < 27:
        hitter = lineup[current_batter_index]
        result = simulate_at_bat(hitter)

        if result == 'hit':
            diamond.hit(hitter)
        elif result == 'double':
            diamond.double(hitter)
        elif result == 'triple':
            diamond.triple(hitter)
        elif result == 'home_run':
            diamond.home_run(hitter)
        elif result == 'base_on_balls':
            diamond.base_on_balls(hitter)
        elif result == 'hit_by_pitch':
            diamond.hit_by_pitch(hitter)
        else:
            diamond.out()

        current_batter_index = (current_batter_index + 1) % len(lineup)

    return diamond.score

def simulate_season(lineup, num_games=162):
    total_score = 0
    for _ in range(num_games):
        total_score += simulate_game(lineup)
    return total_score / num_games

def find_optimal_lineup(players):
    best_lineup = None
    best_score = 0

    for lineup_order in permutations(players):
        avg_score = simulate_season(lineup_order)
        if avg_score > best_score:
            best_score = avg_score
            best_lineup = lineup_order

    return best_lineup, best_score

# 선수 데이터
players_data = [
    Hitter("Ohtani Shohei", plate_appearance=639, at_bat=537, hit=138, double=26, triple=8, home_run=34, bb=96, hbp=5, pace=0.6),
    Hitter("Mike Trout", plate_appearance=507, at_bat=438, hit=123, double=24, triple=1, home_run=40, bb=90, hbp=4, pace=0.5),
    Hitter("Anthony Rendon", plate_appearance=248, at_bat=200, hit=49, double=10, triple=0, home_run=6, bb=23, hbp=1, pace=0.4),
    Hitter("Albert Pujols", plate_appearance=296, at_bat=267, hit=65, double=11, triple=0, home_run=12, bb=14, hbp=5, pace=0.2),
    Hitter("Justin Upton", plate_appearance=362, at_bat=274, hit=63, double=12, triple=0, home_run=17, bb=39, hbp=10, pace=0.3),
    Hitter("Jared Walsh", plate_appearance=454, at_bat=385, hit=98, double=27, triple=2, home_run=15, bb=45, hbp=4, pace=0.3),
    Hitter("David Fletcher", plate_appearance=665, at_bat=603, hit=157, double=26, triple=3, home_run=2, bb=28, hbp=3, pace=0.5),
    Hitter("Max Stassi", plate_appearance=319, at_bat=272, hit=61, double=13, triple=1, home_run=13, bb=38, hbp=7, pace=0.3),
    Hitter("Taylor Ward", plate_appearance=375, at_bat=324, hit=81, double=19, triple=0, home_run=8, bb=38, hbp=7, pace=0.4)
]

# 최적의 타순 찾기
best_lineup, best_score = find_optimal_lineup(players_data)
print("최적의 타순:", [player.name for player in best_lineup])
print("평균 득점:", best_score)
