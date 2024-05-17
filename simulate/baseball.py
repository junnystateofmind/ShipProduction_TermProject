import numpy as np

class Hitter:
    def __init__(self, name, plate_appearance, at_bat, hit, double, triple, home_run, bb, hbp, pace):
        self.name = name
        self.plate_appearance = plate_appearance
        self.at_bat = at_bat
        self.hit = hit
        self.double = double
        self.triple = triple
        self.home_run = home_run
        self.bb = bb
        self.hbp = hbp
        self.pace = pace # 주력에 따라 한 베이스를 더 뛸 수 있는 능력

    def batting_average(self):
        return self.hit / self.at_bat

    def OBP(self):
        return (self.hit + self.bb + self.hbp) / self.plate_appearance

    def SLG(self):
        return (self.hit + self.double + 2 * self.triple + 3 * self.home_run) / self.at_bat # hit에 장타들이 포함되어 있음

    def OPS(self):
        return self.OBP() + self.SLG()

    def single_prob(self):
        return (self.hit - self.double - self.triple - self.home_run) / self.at_bat

    def double_prob(self):
        return self.double / self.at_bat

    def triple_prob(self):
        return self.triple / self.at_bat

    def home_run_prob(self):
        return self.home_run / self.at_bat

    def bb_prob(self):
        return self.bb / self.plate_appearance

    def hbp_prob(self):
        return self.hbp / self.plate_appearance

    def runner_run_when_hit(self): # 안타가 나왔을 때 주자가 한 베이스를 더 뛰는 경우
        return np.random.rand() < self.pace

class Diamond:
    def __init__(self):
        self.base = [None, None, None]  # 1루, 2루, 3루
        self.outs= 0
        self.score = 0

    def clear_base(self):
        self.base = [None, None, None]

    def hit(self, hitter):
        runners = [hitter] + self.base
        self.base = [None, None, None]

        for i in range(3, -1, -1): # 3루 주자부터 1루 주자 순으로 처리
            if runners[i] is not None:
                if i == 3:
                    self.score += 1  # 3루 주자가 홈으로 들어옴
                else:
                    next_base = i + 2 if runners[i].runner_run_when_hit() else i + 1
                    if next_base < 3:
                        self.base[next_base] = runners[i]
                    else:
                        self.score += 1  # 주자가 홈으로 들어옴

    def double(self, hitter):
        runners = [None, hitter] + self.base
        self.base = [None, None, None]

        for i in range(3, -1, -1):
            if runners[i] is not None:
                if i >= 2:
                    self.score += 1  # 2루 이상 주자가 홈으로 들어옴
                else:
                    next_base = i + 2
                    if next_base < 3:
                        self.base[next_base] = runners[i]
                    else:
                        self.score += 1  # 주자가 홈으로 들어옴

    def triple(self, hitter):
        runners = [None, None, hitter] + self.base
        self.base = [None, None, None]

        for i in range(3, -1, -1):
            if runners[i] is not None:
                if i >= 1:
                    self.score += 1  # 1루 이상 주자가 홈으로 들어옴
                else:
                    next_base = i + 3
                    if next_base < 3:
                        self.base[next_base] = runners[i]
                    else:
                        self.score += 1  # 주자가 홈으로 들어옴

    def home_run(self, hitter):
        self.score += 1  # 타자가 홈으로 들어옴
        for runner in self.base:
            if runner is not None:
                self.score += 1  # 모든 주자가 홈으로 들어옴
        self.base = [None, None, None]  # 베이스 비우기

    def base_on_balls(self, hitter):
        next_base = 0
        for i in range(3, -1, -1):
            if self.base[i] is None:
                next_base = i
            else:
                break
        self.base[next_base] = hitter

    def hit_by_pitch(self, hitter):
        next_base = 0
        for i in range(3, -1, -1):
            if self.base[i] is None:
                next_base = i
            else:
                break
        self.base[next_base] = hitter

    def out(self):
        self.outs += 1
        if self.outs % 3 == 0:
            self.clear_base()