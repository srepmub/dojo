from collections import defaultdict
import csv
import io
import functools
from js import document
from pyodide.ffi import create_proxy
from js import document, Uint8Array, File, URL
from pyodide.ffi.wrappers import add_event_listener
import random
import time
import traceback

directions = [(1, 1), (-1, 1), (0, 1), (1, -1), (-1, -1), (0, -1), (1, 0), (-1, 0)]

def do_flip(x, y, color):
    document.getElementById('%d_%d' % (x, y)).color = color
    img = document.getElementById('img%d_%d' % (x, y))
    if color == 'white':
        img.src = 'white.png'
    elif color == 'black':
        img.src = 'black.png'
    else:
        img.src = ''

def flip_in_direction(x, y, direction):
    other_color = False
    while True:
        x, y = x+direction[0], y+direction[1]
        if x not in range(8) or y not in range(8):
            return False
        img = document.getElementById('%d_%d' % (x, y))
        if img.color == 'empty':
            return False
        if img.color != color:
            other_color = True
        else:
            return other_color

def flip_stones(move):
    for direction in directions:
        if flip_in_direction(move[0], move[1], direction):
             x, y = move[0]+direction[0], move[1]+direction[1]
             while document.getElementById('%d_%d' % (x, y)).color != color:
                 do_flip(x, y, color)
                 x, y = x+direction[0], y+direction[1]
    do_flip(move[0], move[1], color)

def possible_move(x, y):
    td = document.getElementById('%d_%d' % (x, y))
    if td.color == 'empty':
        for direction in directions:
            if flip_in_direction(x, y, direction):
                return True

def has_move():
    for x in range(8):
        for y in range(8):
            if possible_move(x, y):
                return True
    return False

def init_board():
    global color, move_nr, illegal

    for x in range(8):
        for y in range(8):
            do_flip(x, y, 'empty')
            cell = document.getElementById('%d_%d' % (x, y))
            cell.style.background = 'green'

    do_flip(3, 3, 'white')
    do_flip(4, 4, 'white')
    do_flip(3, 4, 'black')
    do_flip(4, 3, 'black')

    move_nr = 0
    illegal = 0

    color = 'black'


def exception(function):
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            title = document.getElementById('header')
            title.innerHTML = traceback.format_exc()
            title.style.background = 'red'
            raise
    return wrapper


@exception
def on_select(e):
    on_reset(do_select=True)


@exception
def on_select_color(e):
    global my_color
    my_color = e.target.value
    if color != my_color and my_color != 'both':
        computer_move()


@exception
def on_quiz(e):
    global quizpos, quizsorted
    select = document.getElementById('select')
    if quizpos is None or quizpos == len(quizsorted):
        quizpos = 0
        quizsorted = sorted(lines, key=lambda key: float(lines[key]['score']))
    select.value = quizsorted[quizpos]
    quizpos += 1
    on_reset(do_select=True)


@exception
def on_rnd(e):
    global randompos, randomsorted
    select = document.getElementById('select')
    if randompos is None or quizpos == len(randomsorted):
        randompos = 0
        randomsorted = list(lines)
        random.shuffle(randomsorted)
    select.value = randomsorted[randompos]
    randompos += 1
    on_reset(do_select=True)


@exception
def on_reset(e=None, do_select=False):
    global line, my_color, last_comp, started
    select = document.getElementById('select')
    my_color = lines[select.value]['color']
    line = lines[select.value]['path']
    init_board()
    select_color = document.getElementById('select_color')
    if do_select:
        select_color.value = my_color
    else:
        my_color = select_color.value
    last_comp = None

    if select_start.value == 'from common':
        start_pos = None
        for i in range(0, len(line), 2):
            if len(tree[line[:i+2]]) > 1:
                start_pos = i//2

        if start_pos is not None:
            for i in range(start_pos+1):
                computer_move()
                last_comp.style.background = 'green'

    if my_color != 'both' and color != my_color:
        computer_move()
        last_comp.style.background = 'green'

    title = document.getElementById('header')

    currline = line[:(move_nr-1)*2]
    if currline in tree:
        for path in tree[currline]:
            mv = path[2*(move_nr-1):2*move_nr]
            if mv:
                mvy = ord(mv[0])-ord('A')
                mvx = ord(mv[1])-ord('1')
                cell = document.getElementById('%d_%d' % (mvx, mvy))
                cell.style.background = 'darkgreen'

    if last_comp is not None:
        last_comp.style.background = 'red'

    started = False

    # TODO merge title updates
    title = document.getElementById('header')
    title.innerHTML = 'opening=%s, score=%s' % (lines[select.value]['name'], lines[select.value]['score'])
    title.style.background = 'green'


@exception
def on_click(e):
    global move_nr, t0, illegal, started, color, last_comp
    if not started:
        t0 = time.time()
        started = True

    title = document.getElementById('header')
    if e.target.id.startswith('img'):
        title.innerHTML = 'ILLEGAL MOVE!'
        title.style.background = 'red'
    else:
        x, y = [int(i) for i in e.target.id.split('_')]
        if possible_move(x, y):
            good = line[2*move_nr:2*move_nr+2]
            good_x = ord(good[0])-ord('A')
            good_y = int(good[1])-1
            if (int(x), int(y)) != (good_y, good_x): # TODO swapped
                title.innerHTML = 'WRONG MOVE!'
                title.style.background = 'red'
                illegal += 1
                lines[select.value]['score'] = '1'
            else:
                flip_stones((x, y))

                move_nr += 1
                color = 'black' if color == 'white' else 'white'
                last_comp = None

                if has_move():
                    if color != my_color and move_nr < len(line)//2 and my_color != 'both':
                        computer_move()
                else:
                    color = 'black' if color == 'white' else 'white'

                blackcount = 0
                whitecount = 0

                for u in range(8):
                    for v in range(8):
                        kolor = document.getElementById('%d_%d' % (u, v)).color
                        if kolor == 'white':
                            whitecount += 1
                        elif kolor == 'black':
                            blackcount += 1

                        if move_nr == len(line)//2:
                            document.getElementById('%d_%d' % (u, v)).style.background = 'grey'
                        else:
                            document.getElementById('%d_%d' % (u, v)).style.background = 'green'

                if last_comp is not None:
                    last_comp.style.background = 'red'

                if move_nr == len(line)//2:
                    if illegal == 0:
                        score = float(lines[select.value]['score'])
                        lines[select.value]['score'] = '%.2f' % (min(score * 1.5, 10))

                title.innerHTML = str('time=%.3f white=%d black=%d wrong=%d score=%s' % (time.time()-t0, whitecount, blackcount, illegal, lines[select.value]['score']))
                title.style.background = 'green'
        else:
            title.innerHTML = 'ILLEGAL MOVE!'
            title.style.background = 'red'


def computer_move(red=True):
    global color, move_nr, last_comp

    good = line[2*move_nr:2*move_nr+2]
    good_x = ord(good[0])-ord('A')
    good_y = int(good[1])-1

    flip_stones((good_y, good_x))

    move_nr += 1

    if color == 'black':
        color = 'white'
    else:
        color = 'black'

    cell = document.getElementById('%d_%d' % (good_y, good_x))
    if red:
        cell.style.background = 'red'

    last_comp = cell

board = document.getElementById('board')
for i in range(8):
    tr = document.createElement('tr')
    for j in range(8):
        td = document.createElement('td')
        td.style = 'background: green; border: 1px solid black; padding: 11px'
        td.width = td.height = 80
        td.min_width = td.min_height = 80
        td.align = 'center'
        td.id = '%d_%d' % (i, j)
        td.color = 'empty'
        td.addEventListener('click', create_proxy(on_click))
        img = document.createElement('img')
        img.id = 'img%d_%d' % (i, j)
        td.appendChild(img)
        tr.appendChild(td)
    board.appendChild(tr)


async def upload_file_and_show(e):
    global lines, quizpos, randompos, tree

    try:
        title = document.getElementById('header')
        title.innerHTML = 'start upload..'

        file_list = e.target.files
        first_item = file_list.item(0)
        bio = csv.DictReader(io.StringIO((await get_bytes_from_file(first_item)).decode('utf-8')))

        quizpos = randompos = None

        lines = {}
        tree = defaultdict(list)
        for row in bio:
            lines[row['name']] = row

        select = document.getElementById('select')
        child = select.lastElementChild
        while child:
            select.removeChild(child)
            child = select.lastElementChild

        for line in lines.values():
            option = document.createElement('option')
            option.innerHTML = line['name']
            select.appendChild(option)

            path = line['path']
            for i in range(0, len(path), 2):
                tree[path[:i+2]].append(path)

            line['score'] = '%.2f' % max(float(line['score'])-0.1, 1)

        on_reset(do_select=True)

        ones = len([x for x in lines.values() if float(x['score']) < 5])
        avg = sum([float(x['score']) for x in lines.values()])/len(lines)
        title = document.getElementById('header') # TODO merge
        title.innerHTML = 'loaded %d openings (%.2f avg, %d need work!)' % (len(lines), avg, ones)
        title.style.background = 'green'

    except Exception as e:
        title = document.getElementById('header') # TODO merge
        title.innerHTML = traceback.format_exc()


async def get_bytes_from_file(file):
    array_buf = await file.arrayBuffer()
    return array_buf.to_bytes()


def downloadFile(*args):
    bio = io.StringIO()
    fieldnames = ('path', 'color', 'name', 'score')
    writer = csv.DictWriter(bio, fieldnames)
    writer.writeheader()

    for key in sorted(lines, key=lambda key: float(lines[key]['score'])):
        writer.writerow(lines[key])
    encoded_data = bio.getvalue().encode('utf-8')

    my_stream = io.BytesIO(encoded_data)

    js_array = Uint8Array.new(len(encoded_data))
    js_array.assign(my_stream.getbuffer())

    file = File.new([js_array], "dojo.txt", {type: "text/plain"})
    url = URL.createObjectURL(file)

    hidden_link = document.createElement("a")
    hidden_link.setAttribute("download", "dojo.txt")
    hidden_link.setAttribute("href", url)
    hidden_link.click()


@exception
def main():
    global lines, tree, select, select_start, quizpos, randompos
    quizpos = randompos = None

    lines = {
        'tiger': {'path': 'F5D6C3D3C4', 'name': 'tiger', 'color': 'black', 'score': 1},
        'cow': {'path': 'F5F6E6D6C5', 'name': 'cow', 'color': 'black', 'score': 1},
    }
    tree = defaultdict(list)

    # TODO generic pass-through
    select = document.getElementById('select')
    select.addEventListener('change', create_proxy(on_select))

    select_color = document.getElementById('select_color')
    select_color.addEventListener('change', create_proxy(on_select_color))

    select_start = document.getElementById('select_start')

    reset = document.getElementById('reset')
    reset.addEventListener('click', create_proxy(on_reset))

    quiz = document.getElementById('quiz')
    quiz.addEventListener('click', create_proxy(on_quiz))

    rnd = document.getElementById('rnd')
    rnd.addEventListener('click', create_proxy(on_rnd))

    add_event_listener(document.getElementById("load_db"), "change", upload_file_and_show)
    add_event_listener(document.getElementById("save_db"), "click", downloadFile)

    on_reset(do_select=True)


if __name__ == '__main__':
    main()
