from game import *
if __name__ == '__main__':
    zero = Game.integer(0)
    one = Game.integer(1)
    half = Game.Game([zero], [one])
    print(half.peek())
    two = Game.integer(2)
    print(half*half)

    star = Game.star
    up = Game.up

    quarter = half*half

    print(quarter == Game.Game([zero], [half]))
    eighth = half * quarter
    print(eighth >= Game.Game([zero], [quarter]))

    print(Game.integer(3)+Game.integer(4), "=" ,Game.integer(7), Game.integer(3)+Game.integer(4) == Game.integer(7))

    print(up + up == Game.Game([zero], [up]))
