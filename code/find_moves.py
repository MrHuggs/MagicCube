
# Experimental code to look for combinations that make interesting moves.
# E.g. swap corners and the like.


moves = [
    (('F', 1), [0, 1, 15, 14, 4, 5, 11, 10, 8, 9, 2, 3, 12, 13, 6, 7, 16, 17, 18, 19, 21, 23, 20, 22]),
    (('B', -1), [13, 12, 2, 3, 9, 8, 6, 7, 0, 1, 10, 11, 4, 5, 14, 15, 17, 19, 16, 18, 20, 21, 22, 23]),
    (('B', 1), [8, 9, 2, 3, 12, 13, 6, 7, 5, 4, 10, 11, 1, 0, 14, 15, 18, 16, 19, 17, 20, 21, 22, 23]),
    (('R', -1), [0, 23, 2, 22, 4, 19, 6, 18, 8, 9, 10, 11, 13, 15, 12, 14, 16, 17, 1, 3, 20, 21, 5, 7]),
    (('R', 1), [0, 18, 2, 19, 4, 22, 6, 23, 8, 9, 10, 11, 14, 12, 15, 13, 16, 17, 7, 5, 20, 21, 3, 1]),
    (('L', -1), [16, 1, 17, 3, 20, 5, 21, 7, 10, 8, 11, 9, 12, 13, 14, 15, 6, 4, 18, 19, 2, 0, 22, 23]),
    (('L', 1), [21, 1, 20, 3, 17, 5, 16, 7, 9, 11, 8, 10, 12, 13, 14, 15, 0, 2, 18, 19, 4, 6, 22, 23]),
    (('U', -1), [2, 0, 3, 1, 4, 5, 6, 7, 8, 21, 10, 23, 12, 17, 14, 19, 16, 11, 18, 9, 20, 15, 22, 13]),
    (('U', 1), [1, 3, 0, 2, 4, 5, 6, 7, 8, 19, 10, 17, 12, 23, 14, 21, 16, 13, 18, 15, 20, 9, 22, 11]),
    (('D', -1), [0, 1, 2, 3, 5, 7, 4, 6, 18, 9, 16, 11, 22, 13, 20, 15, 12, 17, 14, 19, 8, 21, 10, 23]),
    (('D', 1), [0, 1, 2, 3, 6, 4, 7, 5, 20, 9, 22, 11, 16, 13, 18, 15, 10, 17, 8, 19, 14, 21, 12, 23]),
]


identity = list(range(0,24))

def score_list(l):
    score = 0
    for i in range(24):
        if l[i] == i:
            score += 1

    return score


def apply_list(p, n):
    res = []
    for i in p:
        res.append(n[i])

    return res

def top_correct(perm):
    for i in range(12):
        if perm[i] != i:
            return False

    return True


def is_twist(perm):

    for  desc, l in moves:

        if (desc[1] < 0):
            continue

        next_l = apply_list(perm, l)
        if score_list(next_l) == len(l):
            return True;


        next_l = apply_list(next_l, l)
        if score_list(next_l) == len(l):
            return True;

        next_l = apply_list(next_l, l)
        if score_list(next_l) == len(l):
            return True;

    return False


def explore(cur, max_path, current_best_score, current_best_path):

    path = cur[0]

    path_len = len(path)
    if (path_len >= max_path):
        return (current_best_score, current_best_path)
    perm = cur[1]

    for  desc, l in moves:

        global best_pair
        global best_score

        next_path = path.copy()
        next_path.append(desc)

        next_l = apply_list(perm, l)

        score = score_list(next_l)

        if score < 24 and score > current_best_score:
            best_score = score
            best_path = (next_path, next_l)
        else:
            best_score = current_best_score
            best_path = current_best_path

        if score >= 12 and score < 24:

            if top_correct(next_l) == False:
                continue

            if score == 12:
                b = is_twist(next_l)
                if (b):
                    #print("This is a twist only.")
                    continue

            print (path_len, score, next_path, next_l)


        new_best_score, new_best_path = explore((next_path, next_l), max_path, best_score, current_best_path)

    return (new_best_score, new_best_path)

best_score, best_path = explore(([moves[0][0]], moves[0][1]), 8, 0, (['base'], moves[0][1]))

print("Complete")
print(best_score, best_path)







