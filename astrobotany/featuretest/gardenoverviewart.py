#! python
from datetime import *
import math
import random
import re

# this file helps in getting a json structure with all plants from astrobotany
# it uses the ignition-gemini packacke from github cbrews/ignition
# getPlants(d=None)
# return plants = json.loads(response.data())['response']
# this data comes from the API endpoint 'api/plants' at 'gemini://astrobotany.mozz.us'
# as well as getting the blessed color as a string
# getBlessedColor(d=None, allcolorDict=None)
# return 'green'
from loadPlants import *


# =========================================================
# there are some constants and functions copied directly from the
# astobotany source

# (no change)
def colorize(text: str, fg = None, bg = None) -> str:
    """
    Colorize a line of text using the ansi-240 color palette.
    """
    if fg is not None:
        text = f"\033[38;5;{fg+15}m" + text
    if bg is not None:
        text = f"\033[48;5;{bg+15}m" + text
    if fg is not None or bg is not None:
        text = text + "\033[0m"
    return text

# (change) Palette mapping for flower colors: (primary, secondary)
# added rainbow colors as well
# this way the color 'rainbow' is also in the dict for parsing the plants
FLOWER_COLORS = {
    "red": (182, 189),
    "orange": (187, 199),
    "yellow": (211, 207),
    "green": (70, 104),
    "blue": (66, 18),
    "indigo": (48, 83),
    "violet": (150, 184),
    "white": (235, 239),
    "black": (224, 228),
    "gold": (163, 165),
    "rainbow": (5, 145, 211, 193, 30, 198, 31)
}

# (change) Attention! this has beed changed slightly!
# rainbow colors are shuffled before use
# to get a different color for each single char plant
def flowerize(text: str, flower_color: str):
    """
    Colorize a text string to match a plant's primary flower color.
    Pronounced "Flower-ize", rhymes with "colorize".
    """
    if flower_color == "rainbow":
        rainbow_colors = list(FLOWER_COLORS["rainbow"])
        random.shuffle(rainbow_colors)
        rainbow_gen = iter(rainbow_colors)
        # rainbow_gen = iter(FLOWER_COLORS["rainbow"])
        return "".join(colorize(char, next(rainbow_gen)) for char in text)
    elif flower_color in FLOWER_COLORS:
        return colorize(text, FLOWER_COLORS[flower_color][0])
    else:
        return text


# =========================================================
# from this point onwards, its new garden overview art stuff

garden_pond = '''
11111111111111111111111111111111111111111111111111
1                                                1
1                                                1
1        ~~~~    ~~~~~~                          1
1       ~~~~~~~~~~~~~~~~~                        1
1        ~~~~~~~~~~~~~~~~                        1
1         ~~~~~~~~~~~~~~                         1
1           ~~~~~~~~~~                           1
1              ~~~~~~                            1
1                                                1
1                                                1
11111111111111111111111111111111111111111111111111
'''

# chars for each plant stage
AGEchar = {
    'seed': ".",
    'seedling': ".",
    'young': "o",
    'mature': "O",
    'flowering': "@",
    'seed-bearing': "&"
}
# age value for lookup and comparison purposes
AGEnum = {
    'seed': 1,
    'seedling': 2,
    'young': 3,
    'mature': 4,
    'flowering': 5,
    'seed-bearing': 6
}

def garden_parsePlant (description):
    # try and match the current info in the description
    # with the dictionaries
    # store the info that was matched in the return value
    info = {
        'age': AGEchar,
        'species': None,
        'color': FLOWER_COLORS,
        'rarity': None,
        'mutation': None
    }

    for k,v in info.items():
        if v != None:
            vals = list(v.keys())
            vals.sort(key=len,reverse=True)
            possibilities = '|'.join(vals)
            pattern = f'\\b({possibilities})+\\b'
            matches = re.findall(pattern,description)
            if len(matches):
                info[k] = matches[0]
            else:
                info[k] = None

    return info

def garden_colorPlants (plants):
    # get the position of a plant
    # parse the plant description
    # set the plant char
    # set the plant color (based on age/dry/description)

    for i in range(len(plants)):
        # get position from url
        # first 4 Hex digits are mapped to a 0..1 position
        # 16bit resolution max
        url = plants[i]['url']
        snips  = url.split('/')
        hex = snips[-1][:4]
        pos = int(hex,16)/2**16
        plants[i]['pos'] = pos
        
        # get plant details such as age, color, etc.
        desc = garden_parsePlant(plants[i]['description'])

        # save age info
        plants[i]['age'] = desc['age']

        # lookup and save age char
        char = AGEchar[desc['age']]
        plants[i]["char"] = char

        # use green color for young plants
        color = desc['color']
        if color == None:
            color = 'green'
        
        # grey for dry plants
        # else use plant color
        # standard astrobotany functions
        if plants[i]["health"] == "dry":
            plants[i]["color"] = colorize(char, 223)
        else:
            plants[i]["color"] = flowerize(char, color)
    
    return plants

def garden_paintPart (target, part, color=None):
    # paint a complete frame "over" existing image
    # these frames all have the same size
    part = part.strip()
    x = 0
    y = 0
    for i in range(len(part)):
        if part[i] == '\n':
            x = 0
            y += 1
        else:
            if part[i] != ' ':
                if part[i].isdigit():
                    # replace digits with empty strings showing the 
                    # browsers background
                    # effectively deleting the border around the image
                    target[y][x] = ' '
                elif color != None and color > 0:
                    target[y][x] = colorize(part[i], color)
                else:
                    target[y][x] = part[i]
            x += 1
    return target

def garden_paintKoi (target, color=None, d=None):
    # paint the koi into the pond in a random position
    # left|right direction of the koi is random
    if d == None:
        d = date.today().strftime("%Y%m%d")
    locations = []
    for i in range(2,len(target)-2):
        for j in range(2,len(target[0])-2):
            posOK = True
            # position is OK when there is at least 
            # 1 wave ~ around the koi on all sides
            # ~~~~~
            # ~<><~
            # ~~~~~
            for k in range(-1,2):
                for l in range(-2,3):
                    if not ('~' in target[i+k][j+l]):
                        posOK = False
                        break
                if not posOK:
                    break
            
            if posOK:
                locations.append((i,j))

    if len(locations):
        random.seed(d)
        choice = random.choice(locations)
        # random direction
        koi = random.choice(['<><', '><>'])
        for i in range(3):
            char = koi[i]
            if color != None and color != '':
                char = flowerize(koi[i], color)
                       
            target[choice[0]][choice[1]-1+i] = char

    return target

def garden_paint (garden_frame, d=None):
    # paint all parts of the garden image into the frame
    # 2 versions: colorless, ANSI

    # create base image, later t stands for user plant
    # image is the colorless version
    # garden is the ANSI color version
    xmax = garden_frame.strip().find('\n')
    ymax = garden_frame.strip().count('\n') + 1
    image = [x[:] for x in [['t'] * xmax] * ymax]
    garden = [x[:] for x in [['t'] * xmax] * ymax]

    # in earlier versions there were multiple 
    # garden parts drawn here
    # e.g. a dedicated frame, extra pathway, added river, etc.
    # but I ended up deleting those in favor of a cleaner look
    image = garden_paintPart(image, garden_pond)
    garden = garden_paintPart(garden, garden_pond, 18)
    
    image = garden_paintKoi (image,None,d)
    garden = garden_paintKoi (garden, getBlessedColor(d,FLOWER_COLORS), d)

    return image, garden

def garden_getJoinedString (image, garden):
    # join all tiles for printing
    image_str = ''
    garden_str = ''
    for i in range(len(image)):
        image_str += '\n' + "".join(image[i])
        garden_str += '\n' + "".join(garden[i])

    return image_str, garden_str

def garden_paintPlants(target_str, plants, colored=False):
    # paint all the plants into the image string
    # only show oldest plant on a spot if there are more than 1

    # count the number of available plant spots
    # create plant array
    max = target_str.count('t')
    plant_arr = [' '] * max
    plant_age = [0] * max

    # check plant age when drawing the tile
    # only the oldest plant on a spot is shown
    # younger plants get "overshadowed"
    for i in range(len(plants)):
        if colored:
            plant_char = plants[i]['color']
        else:
            plant_char = plants[i]['char']
        plant_pos = plants[i]['pos']
        idx = int(math.floor(plant_pos * max))
        age = AGEnum[plants[i]['age']]
        # only draw the oldest plant on any spot
        if age > plant_age[idx]:
            plant_arr[idx] = plant_char
            plant_age[idx] = age

    # paint all plants into the image string
    for i in range(len(plant_arr)):
        target_str = target_str.replace('t',plant_arr[i],1)
    
    return target_str

def garden_paintAllPlants (image_str, garden_str, plants):
    # paint all the plants into the image string
    # 2 versions: colorless, ANSI
    image_str = garden_paintPlants(image_str, plants)
    garden_str = garden_paintPlants(garden_str, plants, True)

    return image_str, garden_str

def garden_exportGMI(image_str, garden_str, d=None):
    # print a basic GMI file to show the garden overview image
    # save to file
    print(image_str)
    if d == None:
        d = date.today().strftime("%Y%m%d")

    path = "history\plants{0}.gmi".format(d)
    with open(path,"w") as f:
        print("## Astrobotany Community Garden\n\n```\n", file=f)
        print(garden_str, file=f)
        print("```\n", file=f)

def garden_createOverview(d=None):
    # get all plants via astrobotany API through gemini request
    allPlants = getPlants(d)
    
    # parse and enrich all plants with proper char and color
    allPlants = garden_colorPlants (allPlants)

    # paint all garden parts into the frame
    # garden_plain, garden_color = garden_paint (garden_frame, d)
    garden_plain, garden_color = garden_paint (garden_pond, d)
    
    # paint the enriched plants into the frame using proper chars and colors
    garden_plain_str, garden_color_str = garden_getJoinedString (garden_plain, garden_color)
    garden_plain_str, garden_color_str = garden_paintAllPlants(garden_plain_str, garden_color_str, allPlants)

    # export a basic GMI file to display in a gemini browser
    garden_exportGMI(garden_plain_str, garden_color_str, d)


# call the garden overview art creation
# only on todays date
# garden_createOverview()

# or on several given dates
# to recalculate files after a code change
dates = ["20211106","20211107","20211108","20211109","20211110","20211111","20211112","20211113","20211114","20211115","20211116","20211117","20211118","20211119","20211120"]
for d in dates:
    garden_createOverview(d)