from __future__ import annotations

import typing
from itertools import product as _product
from itertools import chain as _chain
from itertools import permutations as _permutations
from typing import Callable, Generator, TypeVar
from inspect import signature


X = TypeVar('X')
Y = TypeVar('Y')


# Source code from user Goalsum on stack overflow on April 22nd 2024.
# Link: https://stackoverflow.com/questions/77538000/is-there-a-generic-way-to-make-deep-recursive-functions-work-without-changing-sy
# Source code from Martin Huschenbett
# Link: https://hurryabit.github.io/blog/stack-safety-for-free/
# >> Begin borrowed source code <<
def recursive_one(f: Callable[[X], Generator[X, Y, Y]]) -> Callable[[X], Y]:
    def mu_f(arg: X) -> Y:
        stack = []
        current = f(arg)
        res: B = None  # type: ignore

        while True:
            try:
                arg = current.send(res)
                stack.append(current)
                current = f(arg)
                res = None  # type: ignore
            except StopIteration as stop:
                if len(stack) > 0:
                    current = stack.pop()
                    res = stop.value
                else:
                    return stop.value

    return mu_f
# >> End borrowed source code <<

def recursive_more(f: Callable[[X], Generator[X, Y, Y]]) -> Callable[[X], Y]:
    def mu_f(*args: X) -> Y:
        stack = []
        current = f(*args)
        res: Y = None  # type: ignore

        while True:
            try:
                args = current.send(res)
                stack.append(current)
                current = f(*args)
                res = None  # type: ignore
            except StopIteration as stop:
                if len(stack) > 0:
                    current = stack.pop()
                    res = stop.value
                else:
                    return stop.value

    return mu_f


def recursive(f: Callable[[X], Generator[X, Y, Y]]) -> Callable[[X], Y]:
    match len(signature(f).parameters):
        case 1:
            return recursive_one(f)
        case _:
            return recursive_more(f)


@recursive
def _private_leq(xy: tuple[Game, Game]) -> Generator[[tuple[Game, Game]], bool, bool]:
    x, y = xy
    for xL in x.L:
        if (yield (y, xL)):
            return False
    for yR in y.R:
        if (yield (yR, x)):
            return False
    return True


@recursive
def _private_add(x: Game, y: Game) -> Game:
    L = []
    for xL in x.L:
        L.append((yield xL, y))
    for yL in y.L:
        L.append((yield x, yL))
    R = []
    for xR in x.R:
        R.append((yield xR, y))
    for yR in y.R:
        R.append((yield x, yR))
    return Game(L, R, name="("+str(x)+"+"+str(y)+")")


@recursive
def _private_mul(x: Game, y: Game) -> Game:
    L = []
    for xLR, yLR in _chain(_product(x.L, y.L), _product(x.R, y.R)):
        L.append((yield xLR, y) + (yield yLR, x) - (yield xLR, yLR))
    R = []
    for xLR, yRL in _chain(_product(x.L, y.R), _product(x.R, y.L)):
        R.append((yield xLR, y) + (yield yRL, x) - (yield xLR, yRL))
    return Game(L, R, name=x.peek()+"·"+y.peek())


@recursive
def _private_deep(x: Game, depth: int = -1):
    if depth == 0:
        return str(x)
    str_L = []
    for xL in x.L:
        str_L.append((yield xL, depth-1))
    str_R = []
    for xR in x.R:
        str_R.append((yield xR, depth-1))
    return "{" + ",".join(map(str, str_L)) + "|" + ",".join(map(str, str_R)) + "}"


class Game(object):
    def __init__(x: Game, L: Iterable[Game] = [], R: Iterable[Game] = [], name: str = '', simplified: bool = False):
        if not simplified:
            y = Game(L, R, name, True).simplify()
            x.L = y.L
            x.R = y.R
        else:
            x.L = frozenset(L)
            x.R = frozenset(R)
        x.name = name

    @recursive
    def __str__(x: Game) -> str:
        if x.name:
            return x.name
        str_L = []
        for xL in x.L:
            str_L.append((yield xL))
        str_R = []
        for xR in x.R:
            str_R.append((yield xR))
        return "{" + ",".join(map(str, str_L)) + "|" + ",".join(map(str, str_R)) + "}"

    def deep(x: Game, depth: int = -1) -> str:
        return _private_deep(x, depth)

    def peek(x: Game) -> str:
        return x.deep(1)

    def __hash__(x: Game) -> int:
        return hash(str(x))

    def __le__(x: Game, y: Game) -> bool:
        return _private_leq((x, y))

    def __ge__(x: Game, y: Game) -> bool:
        return y <= x

    def __eq__(x: Game, y: Game) -> bool:
        return x <= y <= x

    def __lt__(x: Game, y: Game) -> bool:
        return x <= y and not y <= x

    def __gt__(x: Game, y: Game) -> bool:
        return y < x

    def __add__(x: Game, y: Game) -> Game:
        return _private_add(x, y)

    @recursive
    def __neg__(x: Game) -> Game:
        L = []
        for xR in x.R:
            L.append((yield -xR))
        R = []
        for xL in x.L:
            R.append((yield -xL))
        return Game(L, R)

    def __sub__(x: Game, y: Game) -> Game:
        return x + (-y)

    def __mul__(x: Game, y: Game) -> Game:
        return _private_mul(x, y)

    def copy(x: Game) -> Game:
        return Game(x.L.copy(), x.R.copy(), name=x.name, simplified=True)

    def bypass(x: Game) -> tuple[Game, bool]:
        changed = False
        R = set(x.R)
        queue = list(x.R)
        while queue:
            xR = queue.pop(0)
            for xRL in xR.L:
                if x <= xRL:
                    R.discard(xR)
                    R |= xRL.R
                    queue += list(xRL.R)
                    changed = True
        L = set(x.L)
        queue = list(x.L)
        while queue:
            xL = queue.pop(0)
            for xLR in xL.R:
                if xLR <= x:
                    L.discard(xL)
                    L |= xLR.L
                    queue += list(xLR.L)
                    changed = True
        return Game(L, R, name=x.name, simplified=True), changed

    def delete_dominated(x: Game) -> tuple[Game, bool]:
        changed = False
        dominated = set()
        queue = list(x.L)
        while queue:
            xL1 = queue.pop(0)
            for xL2 in queue:
                if xL1 <= xL2:
                    dominated.add(xL1)
                    changed = True
                elif xL2 <= xL1:
                    dominated.add(xL2)
                    changed = True
                else:
                    continue
        L = x.L.difference(dominated)
        dominated = set()
        queue = list(x.R)
        while queue:
            xR1 = queue.pop(0)
            for xR2 in queue:
                if xR1 >= xR2:
                    dominated.add(xR1)
                    changed = True
                elif xR2 >= xR1:
                    dominated.add(xR2)
                    changed = True
                else:
                    continue
        R = x.R.difference(dominated)
        return Game(L, R, name=x.name, simplified=True), changed

    # TODO: Something is seriously messed up here (for instance, not able to get 1/8 == 1/2 * 1/4)
    # Either it has to do with Game.simplify, or it has to do with mutability stuff with the frozensets, idk...
    def simplify(x: Game) -> Game:
        changed = True
        y = x.copy()
        while changed:
            y, changed1 = y.delete_dominated()
            y, changed2 = y.bypass()
            changed = changed1 or changed2
        return y


@recursive
def integer(n: int) -> Generator[int, Game, Game]:
    if n>0:
        return Game(L=[(yield n-1)], name=str(n), simplified=True)
    elif n<0:
        return Game(R=[(yield n+1)], name=str(n), simplified=True)
    else:
        return Game(name="0", simplified=True)


@recursive
def nimber(n: int) -> Generator[int, Game, Game]:
    assert n >= 0
    name = "*"+str(n)
    if n == 0:
        return Game(name=name)
    else:
        S = []
        for i in range(n):
            S.append((yield i))
        return Game(L=S, R=S, name=name)

star = Game([integer(0)], [integer(0)], name="*", simplified=True)
up = Game([integer(0)], [star], name="↑", simplified=True)

############################################################################################

# Testing


@recursive
def Ackermann(m: int, n: int) -> int:
    if m == 0:
        return n+1
    elif n == 0:
        return (yield m, 1)
    else:
        return (yield m, (yield m+1, n))
