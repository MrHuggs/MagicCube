#----------------------------------------------------------------------
# Matplotlib Rubik's cube simulator
# Written by Jake Vanderplas
# Adapted from cube code written by David Hogg
#   https://github.com/davidwhogg/MagicCube


# http://kociemba.org/computervision.html

from __future__ import annotations
from msilib import sequence
from tkinter.ttk import LabeledScale
from xml.sax.handler import feature_string_interning
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import widgets
from matplotlib.patches import Rectangle, PathPatch
from matplotlib.text import TextPath
from matplotlib.transforms import Affine2D
from projection import Quaternion, project_points


labels3x3 = {
0:	1,
1:	2,
2:	3,
3:	4,
4:	'top',
5:	5,
6:	6,
7:	7,
8:	8,
9:	46,
10:		47,
11:		48,
12:		44,
13:		'bottom',
14:		45,
15:		41,
16:		42,
17:		43,
18:		14,
19:		12,
20:		9,
21:		15,
22:		'left',
23:		10,
24:		16,
25:		13,
26:		11,
27:		32,
28:		29,
29:		27,
30:		31,
31:		'right',
32:		26,
33:		30,
34:		28,
35:		25,
36:		40,
37:		37,
38:		35,
39:		39,
40:		'erear',
41:		34,
42:		38,
43:		36,
44:		33,
45:		22,
46:		20,
47:		17,
48:		23,
49:		'front',
50:	    18,
51:	    24,
52:	    21,
53: 	19,
    }

def translateid(faceid):
    if N == 3:
        return labels3x3[faceid - 1]
    else:
        return faceid


def point_action(point, perm):

    return perm[point - 1]

def perm_orbits(perm):
    result = []
    seen = set()

    orbit_start = 1

    while len(seen) < len(perm):
        
        if orbit_start in seen:
            orbit_start += 1
            continue

        orbit = [orbit_start]
        seen.add(orbit_start)

        point = orbit_start

        while True:
            point = point_action(point, perm)

            if point == orbit_start:
                break

            orbit.append(point)
            seen.add(point)

        result.append(orbit)
        orbit_start += 1

    return result


def perm_to_string(perm):

    orbits = perm_orbits(perm)
    
    result = '['
    for orbit in orbits:

        if len(orbit) == 1:
            continue
        
        torbit = [str(translateid(p)) for p in orbit]

        result = result + "[" + ",".join(torbit) + "]"
        

    result = result + ']'
    
    return result
   

def xperm_to_string(perm):
    orbits = perm_orbits(perm)

    result = '['
    for orbit in orbits:

        if len(orbit) == 1:
            continue

        result = result + str(orbit)


    result = result + ']'
    return result

"""
Sticker representation
----------------------
Each face is represented by a length [5, 3] array:

  [v1, v2, v3, v4, v1]

Each sticker is represented by a length [9, 3] array:

  [v1a, v1b, v2a, v2b, v3a, v3b, v4a, v4b, v1a]

In both cases, the first point is repeated to close the polygon.

Each face also has a centroid, with the face number appended
at the end in order to sort correctly using lexsort.
The centroid is equal to sum_i[vi].

Colors are accounted for using color indices and a look-up table.

With all faces in an NxNxN cube, then, we have three arrays:

  centroids.shape = (6 * N * N, 4)
  faces.shape = (6 * N * N, 5, 3)
  stickers.shape = (6 * N * N, 9, 3)
  colors.shape = (6 * N * N,)

The canonical order is found by doing

  ind = np.lexsort(centroids.T)

After any rotation, this can be used to quickly restore the cube to
canonical position.
"""

class Cube:
    """Magic Cube Representation"""
    # define some attribues
    default_plastic_color = 'black'
    

    # This produces the standard wester color scheme:
    # https://getgocube.com/play/japanese-vs-western-colors/
    # w       - white
    # #ffcf00 - yellow
    # #00008f - blue (add8e6 - light blue)
    # #009f0f - green
    # #cf0000 - red
    # #ff6f00 - orange

    default_face_colors = ["w", "#ffcf00",
                           "#ff6f00", "#cf0000",
                           "#add8e6", "#009f0f",
                           "gray", "none"]
    
    base_face = np.array([[1, 1, 1],
                          [1, -1, 1],
                          [-1, -1, 1],
                          [-1, 1, 1],
                          [1, 1, 1]], dtype=float)
    stickerwidth = 0.9
    stickermargin = 0.5 * (1. - stickerwidth)
    stickerthickness = 0.001
    (d1, d2, d3) = (1 - stickermargin,
                    1 - 2 * stickermargin,
                    1 + stickerthickness)
    base_sticker = np.array([[d1, d2, d3], [d2, d1, d3],
                             [-d2, d1, d3], [-d1, d2, d3],
                             [-d1, -d2, d3], [-d2, -d1, d3],
                             [d2, -d1, d3], [d1, -d2, d3],
                             [d1, d2, d3]], dtype=float)

    base_face_centroid = np.array([[0, 0, 1]])
    base_sticker_centroid = np.array([[0, 0, 1 + stickerthickness]])

    # Define rotation angles and axes for the six sides of the cube
    x, y, z = np.eye(3)
    rots = [Quaternion.from_v_theta(np.eye(3)[0], theta)
    for theta in (np.pi / 2, -np.pi / 2)]
    rots += [Quaternion.from_v_theta(np.eye(3)[1], theta)
    for theta in (np.pi / 2, -np.pi / 2, np.pi, 2 * np.pi)]

    # define face movements
    facesdict = dict(F=z, B=-z,
                     R=x, L=-x,
                     U=y, D=-y)

    def __init__(self, N=3, plastic_color=None, face_colors=None):
        self.N = N
        if plastic_color is None:
            self.plastic_color = self.default_plastic_color
        else:
            self.plastic_color = plastic_color

        if face_colors is None:
            self.face_colors = self.default_face_colors
        else:
            self.face_colors = face_colors

        self._move_list = []
        self._initialize_arrays()

    def _initialize_arrays(self):
        # initialize centroids, faces, and stickers.  We start with a
        # base for each one, and then translate & rotate them into position.

        # Define N^2 translations for each face of the cube
        cubie_width = 2. / self.N
        translations = np.array([[[-1 + (i + 0.5) * cubie_width,
                                   -1 + (j + 0.5) * cubie_width, 0]]
                                 for i in range(self.N)
                                 for j in range(self.N)])

        # Create arrays for centroids, faces, stickers, and colors
        face_centroids = []
        faces = []
        sticker_centroids = []
        stickers = []
        colors = []

        factor = np.array([1. / self.N, 1. / self.N, 1])

        for i in range(6):
            M = self.rots[i].as_rotation_matrix()
            faces_t = np.dot(factor * self.base_face
                             + translations, M.T)
            stickers_t = np.dot(factor * self.base_sticker
                                + translations, M.T)
            face_centroids_t = np.dot(self.base_face_centroid
                                      + translations, M.T)
            sticker_centroids_t = np.dot(self.base_sticker_centroid
                                         + translations, M.T)
            colors_i = i + np.zeros(face_centroids_t.shape[0], dtype=int)

            # append face ID to the face centroids for lex-sorting
            face_centroids_t = np.hstack([face_centroids_t.reshape(-1, 3),
                                          colors_i[:, None]])
            sticker_centroids_t = sticker_centroids_t.reshape((-1, 3))

            faces.append(faces_t)
            face_centroids.append(face_centroids_t)
            stickers.append(stickers_t)
            sticker_centroids.append(sticker_centroids_t)
            colors.append(colors_i)

        self._face_centroids = np.vstack(face_centroids)
        self._faces = np.vstack(faces)
        self._sticker_centroids = np.vstack(sticker_centroids)
        self._stickers = np.vstack(stickers)
        self._colors = np.concatenate(colors)

        self._sort_faces()

    def _sort_faces(self):
        # use lexsort on the centroids to put faces in a standard order.
        ind = np.lexsort(self._face_centroids.T)
        self._face_centroids = self._face_centroids[ind]
        self._sticker_centroids = self._sticker_centroids[ind]
        self._stickers = self._stickers[ind]
        self._colors = self._colors[ind]
        self._faces = self._faces[ind]

    def match(self, other):
        
        result = []

        for s in range(self.N * self.N * 6):
            match = False
            for t in range(self.N * self.N * 6):

                cmatch = True
                for i in range(9):
                    pmatch = False
                    for j in range(9):
                        if np.allclose(self._stickers[s,i], other._stickers[t,j], .01, .01):
                            pmatch = True
                            break

                    if pmatch == False:
                        cmatch = False
                        break

                if cmatch == True:
                    match = True
                    #print(s, t)
                    result.append(t + 1)
                    break

            if match == False:
                print ("No match for ", s)

        if len(result) == self.N * self.N * 6:
            return result

        return None


    def rotate_face(self, f, n=1, layer=0):
        """Rotate Face"""
        if layer < 0 or layer >= self.N:
            raise ValueError('layer should be between 0 and N-1')

        try:
            f_last, n_last, layer_last = self._move_list[-1]
        except:
            f_last, n_last, layer_last = None, None, None

        if (f == f_last) and (layer == layer_last):
            ntot = (n_last + n) % 4
            if abs(ntot - 4) < abs(ntot):
                ntot = ntot - 4
            if np.allclose(ntot, 0):
                self._move_list = self._move_list[:-1]
            else:
                self._move_list[-1] = (f, ntot, layer)
        else:
            self._move_list.append((f, n, layer))
        
        v = self.facesdict[f]
        r = Quaternion.from_v_theta(v, n * np.pi / 2)
        M = r.as_rotation_matrix()

        proj = np.dot(self._face_centroids[:, :3], v)
        cubie_width = 2. / self.N
        flag = ((proj > 0.9 - (layer + 1) * cubie_width) &
                (proj < 1.1 - layer * cubie_width))

        for x in [self._stickers, self._sticker_centroids,
                  self._faces]:
            x[flag] = np.dot(x[flag], M.T)
        self._face_centroids[flag, :3] = np.dot(self._face_centroids[flag, :3],
                                                M.T)

    def draw_interactive(self):
        fig = plt.figure(figsize=(5, 5))
        fig.add_axes(InteractiveCube(self))
        return fig


class InteractiveCube(plt.Axes):
    def __init__(self, cube=None,
                 interactive=True,
                 view=(0, 0, 10),
                 fig=None, rect=[0, 0.16, 1, 0.84],
                 **kwargs):
        if cube is None:
            self.cube = Cube(3)
        elif isinstance(cube, Cube):
            self.cube = cube
        else:
            self.cube = Cube(cube)

        self._view = view
        self._start_rot = Quaternion.from_v_theta((1, -1, 0),
                                                  -np.pi / 6)

        if fig is None:
            fig = plt.gcf()

        # disable default key press events
        callbacks = fig.canvas.callbacks.callbacks
        del callbacks['key_press_event']

        # add some defaults, and draw axes
        kwargs.update(dict(aspect=kwargs.get('aspect', 'equal'),
                           xlim=kwargs.get('xlim', (-2.0, 2.0)),
                           ylim=kwargs.get('ylim', (-2.0, 2.0)),
                           frameon=kwargs.get('frameon', False),
                           xticks=kwargs.get('xticks', []),
                           yticks=kwargs.get('yticks', [])))
        super(InteractiveCube, self).__init__(fig, rect, **kwargs)
        self.xaxis.set_major_formatter(plt.NullFormatter())
        self.yaxis.set_major_formatter(plt.NullFormatter())

        self._start_xlim = kwargs['xlim']
        self._start_ylim = kwargs['ylim']

        # Define movement for up/down arrows or up/down mouse movement
        self._ax_UD = (1, 0, 0)
        self._step_UD = 0.01

        # Define movement for left/right arrows or left/right mouse movement
        self._ax_LR = (0, -1, 0)
        self._step_LR = 0.01

        self._ax_LR_alt = (0, 0, 1)

        # Internal state variable
        self._active = False  # true when mouse is over axes
        self._button1 = False  # true when button 1 is pressed
        self._button2 = False  # true when button 2 is pressed
        self._event_xy = None  # store xy position of mouse event
        self._shift = False  # shift key pressed
        self._digit_flags = np.zeros(10, dtype=bool)  # digits 0-9 pressed

        self._current_rot = self._start_rot  #current rotation state
        self._face_polys = None
        self._sticker_polys = None
        self._labels = None

        self._draw_cube()

        # connect some GUI events
        self.figure.canvas.mpl_connect('button_press_event',
                                       self._mouse_press)
        self.figure.canvas.mpl_connect('button_release_event',
                                       self._mouse_release)
        self.figure.canvas.mpl_connect('motion_notify_event',
                                       self._mouse_motion)
        self.figure.canvas.mpl_connect('key_press_event',
                                       self._key_press)
        self.figure.canvas.mpl_connect('key_release_event',
                                       self._key_release)

        self._initialize_widgets()

        # write some instructions
        self.figure.text(0.05, 0.05,
                         "Mouse/arrow keys adjust view\n"
                         "U/D/L/R/B/F keys turn faces\n"
                         "(hold shift for counter-clockwise)",
                         size=10)

    def _initialize_widgets(self):
        bwidth = .1
        bspace = .0
        bstart = .55
        bheight = .075
        self._ax_reset = self.figure.add_axes([bstart + bwidth + bspace, .05 + bheight, bwidth, bheight])
        self._btn_reset = widgets.Button(self._ax_reset, 'Reset\nView')
        self._btn_reset.on_clicked(self._reset_view)

        self._ax_solve = self.figure.add_axes([bstart, 0.05,bwidth, bheight])
        self._btn_solve = widgets.Button(self._ax_solve, 'Solve\nCube')
        self._btn_solve.on_clicked(self._solve_cube)

        self._ax_gens = self.figure.add_axes([bstart + bwidth + bspace, 0.05, bwidth, bheight])
        self._btn_gens = widgets.Button(self._ax_gens, 'Gens')
        self._btn_gens.on_clicked(self.find_generators)
        
        self._ax_gens = self.figure.add_axes([bstart + 2 * bwidth + 2* bspace, 0.05, bwidth, bheight])
        self._btn_gens = widgets.Button(self._ax_gens, 'Save\nImage')
        self.image_count = 0
        self._btn_gens.on_clicked(self.save_image)

        self._apply_ops = self.figure.add_axes([bstart, .05 + bheight, bwidth, bheight])
        
        if self.cube.N == 2:
            self.current_op = 4
        else:        
            self.current_op = 0
        self.ops_text = self.figure.text(0.05, 0.9, "", size=10, wrap = True)
        self._btn_apply_ops = widgets.Button(self._apply_ops, 'Opp {0}'.format(self.current_op))
        self._btn_apply_ops.on_clicked(self.apply_opps)

    def _project(self, pts):
        return project_points(pts, self._current_rot, self._view, [0, 1, 0])

    def _draw_cube(self):
        stickers = self._project(self.cube._stickers)[:, :, :2]
        faces = self._project(self.cube._faces)[:, :, :2]
        face_centroids = self._project(self.cube._face_centroids[:, :3])
        sticker_centroids = self._project(self.cube._sticker_centroids[:, :3])

        plastic_color = self.cube.plastic_color
        colors = np.asarray(self.cube.face_colors)[self.cube._colors]
        face_zorders = -face_centroids[:, 2]
        sticker_zorders = -sticker_centroids[:, 2]

        if self._face_polys is None:
            # initial call: create polygon objects and add to axes
            self._face_polys = []
            self._sticker_polys = []
            self._labels = []

            index = 1

            for i in range(len(colors)):
                fp = plt.Polygon(faces[i], facecolor=plastic_color,
                                 zorder=face_zorders[i])
                sp = plt.Polygon(stickers[i], facecolor=colors[i],
                                 zorder=sticker_zorders[i])

                #lb = self.figure.text(0.2, 0.2 + i * .05, str(i), size=10)
                lb = self.annotate(translateid(i + 1), xy=sticker_centroids[i][:2], textcoords='data')

                self._face_polys.append(fp)
                self._sticker_polys.append(sp)
                self._labels.append(lb)
                self.add_patch(fp)
                self.add_patch(sp)
                
        else:
            # subsequent call: update the polygon objects
            for i in range(len(colors)):
                self._face_polys[i].set_xy(faces[i])
                self._face_polys[i].set_zorder(face_zorders[i])
                self._face_polys[i].set_facecolor(plastic_color)

                self._sticker_polys[i].set_xy(stickers[i])
                self._sticker_polys[i].set_zorder(sticker_zorders[i])
                self._sticker_polys[i].set_facecolor(colors[i])

                #self._labels[i].set_position((sticker_centroids[i][0], sticker_centroids[i][1]))

                self._labels[i].set_position(sticker_centroids[i][:2])
                self._labels[i].set_zorder(face_zorders[i] + .1)


        self.figure.canvas.draw()

    def rotate(self, rot):
        self._current_rot = self._current_rot * rot

    def rotate_face(self, face, turns=1, layer=0, steps=5):
        if not np.allclose(turns, 0):
            for i in range(steps):
                self.cube.rotate_face(face, turns * 1. / steps,
                                      layer=layer)
                self._draw_cube()

    def _reset_view(self, *args):
        self.set_xlim(self._start_xlim)
        self.set_ylim(self._start_ylim)
        self._current_rot = self._start_rot
        self._draw_cube()

    def _solve_cube(self, *args):
        move_list = self.cube._move_list[:]
        for (face, n, layer) in move_list[::-1]:
            self.rotate_face(face, -n, layer, steps=3)
        self.cube._move_list = []
        self.ops_text.set_text("")

    def _key_press(self, event):
        """Handler for key press events"""
        if event.key == 'shift':
            self._shift = True
        elif event.key.isdigit():
            self._digit_flags[int(event.key)] = 1
        elif event.key == 'right':
            if self._shift:
                ax_LR = self._ax_LR_alt
            else:
                ax_LR = self._ax_LR
            self.rotate(Quaternion.from_v_theta(ax_LR,
                                                5 * self._step_LR))
        elif event.key == 'left':
            if self._shift:
                ax_LR = self._ax_LR_alt
            else:
                ax_LR = self._ax_LR
            self.rotate(Quaternion.from_v_theta(ax_LR,
                                                -5 * self._step_LR))
        elif event.key == 'up':
            self.rotate(Quaternion.from_v_theta(self._ax_UD,
                                                5 * self._step_UD))
        elif event.key == 'down':
            self.rotate(Quaternion.from_v_theta(self._ax_UD,
                                                -5 * self._step_UD))
        elif event.key.upper() in 'LRUDBF':
            if self._shift:
                direction = -1
            else:
                direction = 1

            if np.any(self._digit_flags[:N]):
                for d in np.arange(N)[self._digit_flags[:N]]:
                    self.rotate_face(event.key.upper(), direction, layer=d)
            else:
                self.rotate_face(event.key.upper(), direction)

            oc = Cube(self.cube.N)
            perm = self.cube.match(oc)
            print(perm_to_string(perm), " = ", perm)
                
        self._draw_cube()

    def find_generators(self, *args):

        print("Finding generators.")

        base_cube = Cube(self.cube.N)
        sequences = []
        names = []
        
        cformat = False
        for face, axis in self.cube.facesdict.items():
            #for i in range(-1, 2, 2):
            for i in range(1,2):                

                oc = Cube(self.cube.N)

                steps = 5
                
                for s in range(steps):
                    oc.rotate_face(face, i  /steps)

                matches = oc.match(base_cube)
                
                if cformat == True:
                    name = "{{ \"{0}\", {1}),}}".format(face, i)
                    seq = "{"
                    for idx, num in enumerate(matches):
                        seq += " /*{0:2}*/ {1:2},".format(idx, translateid(num))

                    seq += "},"
                    seq = "/*{0:2} - {1:2} : {2:2} */ \t".format(len(sequences), face, i) + seq
                else:
                    name = "{0}{1},".format(face, i)

                    
                    seq = "["
                    for idx, num in enumerate(matches):
                        seq += " {0},".format(translateid(num))

                    seq += "],"
                    seq = seq + "#*{0:2} - {1:2} : {2:2} = {3}".format(len(sequences), face, i, perm_to_string(matches))
                    
                    seq = perm_to_string(matches) + " # " + name

                names.append(name)
                sequences.append(seq)


        for name in names:
            print(name)

        for seq in sequences:
            print(seq)

    def apply_string(self, s):
        
        trans_table = { 
            'f' : "F",
            'b' : "B",
            'l' : "L",
            'r' : "R",
            't' : "U",
            'e' : "D",
            }
        
        for op in s.split(" * "):
            if op[0] == '(':
                face = op[1] #trans_table[op[1]]
                count = 1
                dir = -1
            else:                
                face = op[0] # trans_table[op[0]]
                if len(op) > 1:
                    count = int(op[1])
                else:
                    count = 1
                dir = 1
                
            print("Applying {0} : {1} {2} times".format(face, dir, count))
            for i in range(count):
                self.cube.rotate_face(face, dir)


    def apply_opps(self, *args):
        
        self._solve_cube();
        ops = [ 
		        "L * (B)^-1 * L * (B)^-1 * (R)^-1 * (U)^-1 * R * B2 * L2 * D * F * D * F * (D)^-1 * (F)^-1 * (D)^-1",
		        "F * (D)^-1 * F * D * (F)^-1 * R2 * (D)^-1 * (B)^-1 * D * B * R2 * D * F * D2 * (F)^-1 * D * (F)^-1",
		        "F * R * F * (R)^-1 * (D)^-1 * (F)^-1 * L * D * (L)^-1 * D * L * D2 * (L)^-1 * D2 * F * D * R * (F)^-1 * (R)^-1 * D2 * (F)^-1 * (D)^-1 * F * (D)^-1 * (F)^-1 * D2",
		        "(D)^-1 * F * D * (F)^-1 * R2 * (D)^-1 * (B)^-1 * D * B * R2 * D * F * D2 * (F)^-1 * D",
		        "F * R * F * (R)^-1 * (F)^-1 * L * F2 * (D)^-1 * (F)^-1 * R * (F)^-1 * (R)^-1 * (L)^-1",
		        "F * B2 * D * (F)^-1 * (D)^-1 * B2 * D2 * (R)^-1 * (D)^-1 * F * (D)^-1 * (F)^-1",
		        "F * D * R * F * (R)^-1 * (D)^-1 * (F)^-1 * D * F * D * (F)^-1 * D * F * D * (F)^-1"            
               ]

        s = ops[self.current_op]
        self.apply_string(s)
                
        self._draw_cube()
        
        oc = Cube(self.cube.N)
        perm = self.cube.match(oc)
        
        perm_string = perm_to_string(perm)
        self.ops_text.set_text(s + "\n" + perm_string)
        
        fname = "{0}Opp{1}.png".format(self.cube.N, self.current_op)
        print("Save to file ", fname)
        plt.savefig(fname)
        
        self.current_op = (self.current_op + 1) % len(ops)
        self._btn_apply_ops.label._text = 'Opp {0}'.format(self.current_op)
        
        print("--------------------------------------------------------------")
        print(s)
        print(perm_string, " = ", perm)
        
    def save_image(self, *args):
         plt.savefig("Image{0}.png".format(self.image_count))
         self.image_count += 1

    def _key_release(self, event):
        """Handler for key release event"""
        if event.key == 'shift':
            self._shift = False
        elif event.key.isdigit():
            self._digit_flags[int(event.key)] = 0

    def _mouse_press(self, event):
        """Handler for mouse button press"""
        self._event_xy = (event.x, event.y)
        if event.button == 1:
            self._button1 = True
        elif event.button == 3:
            self._button2 = True

    def _mouse_release(self, event):
        """Handler for mouse button release"""
        self._event_xy = None
        if event.button == 1:
            self._button1 = False
        elif event.button == 3:
            self._button2 = False

    def _mouse_motion(self, event):
        """Handler for mouse motion"""
        if self._button1 or self._button2:
            dx = event.x - self._event_xy[0]
            dy = event.y - self._event_xy[1]
            self._event_xy = (event.x, event.y)

            if self._button1:
                if self._shift:
                    ax_LR = self._ax_LR_alt
                else:
                    ax_LR = self._ax_LR
                rot1 = Quaternion.from_v_theta(self._ax_UD,
                                               self._step_UD * dy)
                rot2 = Quaternion.from_v_theta(ax_LR,
                                               self._step_LR * dx)
                self.rotate(rot1 * rot2)

                self._draw_cube()

            if self._button2:
                factor = 1 - 0.003 * (dx + dy)
                xlim = self.get_xlim()
                ylim = self.get_ylim()
                self.set_xlim(factor * xlim[0], factor * xlim[1])
                self.set_ylim(factor * ylim[0], factor * ylim[1])

                self.figure.canvas.draw()

if __name__ == '__main__':
    import sys
    global N
    
    try:
        N = int(sys.argv[1])
    except:
        N = 3

    c = Cube(N)

    # do a 3-corner swap
    #c.rotate_face('R')
    #c.rotate_face('D')
    #c.rotate_face('R', -1)
    #c.rotate_face('U', -1)
    #c.rotate_face('R')
    #c.rotate_face('D', -1)
    #c.rotate_face('R', -1)
    #c.rotate_face('U')

    c.draw_interactive()

    plt.show()
