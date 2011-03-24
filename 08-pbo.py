#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
08-pbo.py

OpenGL 2.1 pixel operations using PBOs

Copyright (c) 2010, Renaud Blanch <rndblnch at gmail dot com>
Licence: GPLv3 or higher <http://www.gnu.org/licenses/gpl.html>
"""


# imports ####################################################################

import os
import sys

from math import exp, modf
from time import time
from ctypes import sizeof, c_float, c_void_p, c_uint, string_at

from OpenGL.GLUT import *
from OpenGL.GL import *

from linalg import matrix as m
from linalg import quaternion as q

import cube

# shader #####################################################################

def create_shader(shader_type, source):
	"""compile a shader."""
	shader = glCreateShader(shader_type)
	glShaderSource(shader, source)
	glCompileShader(shader)
	if glGetShaderiv(shader, GL_COMPILE_STATUS) != GL_TRUE:
		raise RuntimeError(glGetShaderInfoLog(shader))
	return shader


attribs = [b"vertex", b"tex_coord", b"normal", b"color"]
locations = dict((k, v) for (v, k) in enumerate(attribs))
uniforms = [b"lighting", b"texturing", b"texture_3d"]

def init_program():
	vert_shader = create_shader(GL_VERTEX_SHADER, b"""
		uniform bool lighting;
		
		attribute vec3 vertex;
		attribute vec3 tex_coord;
		attribute vec3 normal;
		attribute vec3 color;
		
		varying vec3 N, L, S;
		
		void main() {
			gl_Position = gl_ModelViewProjectionMatrix * vec4(vertex, 1.);
			gl_TexCoord[0] = gl_TextureMatrix[0] * vec4(tex_coord, 1.);
			
			if(lighting) {
				N = normalize(gl_NormalMatrix*normal);
				L = normalize(gl_LightSource[0].position.xyz);
				S = normalize(gl_LightSource[0].halfVector.xyz);
			}
			gl_FrontColor = vec4(color, 1.);
		}
	""")
	
	frag_shader = create_shader(GL_FRAGMENT_SHADER, b"""
		const float alpha_threshold = .55;
		
		uniform bool texturing;
		uniform sampler3D texture_3d;
		uniform bool lighting;
		
		varying vec3 N, L, S;
		
		void main() {
			if(texturing) {
				vec4 texture_color = texture3D(texture_3d, gl_TexCoord[0].stp);
				if(texture_color.a <= alpha_threshold)
					discard;				
			}

			vec4 color = gl_Color;
			if(lighting) {
				vec4 ambient = color * gl_LightModel.ambient;
				vec4 diffuse = color * gl_LightSource[0].diffuse;
				vec4 specular = gl_FrontMaterial.specular * gl_LightSource[0].specular;
				float d = max(0., dot(N, L));
				float s = pow(max(0., dot(N, S)), gl_FrontMaterial.shininess);
				color = clamp(ambient + diffuse * d + specular * s, 0., 1.);
			}
			gl_FragColor = color;
		}
	""")
	
	program = glCreateProgram()
	glAttachShader(program, vert_shader)
	glAttachShader(program, frag_shader)
	
	for attrib in attribs:
		glBindAttribLocation(program, locations[attrib], attrib)
	
	glLinkProgram(program)
	if glGetProgramiv(program, GL_LINK_STATUS) != GL_TRUE:
		raise RuntimeError(glGetProgramInfoLog(program))
	
	for uniform in uniforms:
		locations[uniform] = glGetUniformLocation(program, uniform)
	
	glUseProgram(program)


# texture ####################################################################

def init_texture():
	glEnable(GL_TEXTURE_3D)
	
	glActiveTexture(GL_TEXTURE0+0)
	glBindTexture(GL_TEXTURE_3D, glGenTextures(1))
	glUniform1i(locations[b"texture_3d"], 0)
	
	glTexParameter(GL_TEXTURE_3D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
	glTexParameter(GL_TEXTURE_3D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
	
	def pixel(i, j, k, opaque=b'\xff\xff', transparent=b'\xff\x00'):
		return opaque if (i+j+k)%2 == 0 else transparent
	
	pixel_buffer = glGenBuffers(1)
	glBindBuffer(GL_PIXEL_UNPACK_BUFFER, pixel_buffer)

	width = height = depth = 2
	glBufferData(GL_PIXEL_UNPACK_BUFFER,
	             width*height*depth*2,
	             b"".join(pixel(i, j, k) for i in range(width)
	                                     for j in range(height)
	                                     for k in range(depth)),
	             GL_STREAM_DRAW)

	glTexImage3D(GL_TEXTURE_3D, 0, GL_LUMINANCE_ALPHA,
	             width, height, depth,
	             0, GL_LUMINANCE_ALPHA, GL_UNSIGNED_BYTE,
	             None)
	
	glBindBuffer(GL_PIXEL_UNPACK_BUFFER, 0)
	glDeleteBuffers(1, [pixel_buffer])
	
	glDisable(GL_TEXTURE_3D)


def animate_texture(fps=25, period=10):
	f, _ = modf(time()/period)
	
	glMatrixMode(GL_TEXTURE)
	glLoadIdentity()
	glTranslate(f, f, f)
	glRotate(f*360, 1, 1, 1)
	f = abs(f*2-1)
	glScale(1+f, 1+f, 1+f)
	
	glutPostRedisplay()
	if texturing:
		glutTimerFunc(int(1000/fps), animate_texture, fps)


# object #####################################################################

def flatten(*lll):
	return [u for ll in lll for l in ll for u in l]


def init_object(model=cube):
	# enabling arrays
	for attrib in attribs:
		glEnableVertexAttribArray(locations[attrib])
	
	# model data
	global sizes
	sizes, indicies = model.sizes, model.indicies
	data = flatten(*zip(model.verticies, model.tex_coords,
	                    model.normals, model.colors))
	
	# loading buffers
	indices_buffer = (c_uint*len(indicies))(*indicies)
	data_buffer = (c_float*len(data))(*data)
	
	glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, glGenBuffers(1))
	glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices_buffer, GL_STATIC_DRAW)
	
	glBindBuffer(GL_ARRAY_BUFFER, glGenBuffers(1))
	glBufferData(GL_ARRAY_BUFFER, data_buffer, GL_STATIC_DRAW)
	
	del indices_buffer
	del data_buffer


uint_size  = sizeof(c_uint)
float_size = sizeof(c_float)
vertex_offset    = c_void_p(0 * float_size)
tex_coord_offset = c_void_p(3 * float_size)
normal_offset    = c_void_p(6 * float_size)
color_offset     = c_void_p(9 * float_size)
record_len       =         12 * float_size

def draw_object():
	glVertexAttribPointer(locations[b"vertex"], 3, GL_FLOAT, False,
	                      record_len, vertex_offset)
	glVertexAttribPointer(locations[b"tex_coord"], 3, GL_FLOAT, False,
	                      record_len, tex_coord_offset)
	glVertexAttribPointer(locations[b"normal"], 3, GL_FLOAT, False,
	                      record_len, normal_offset)
	glVertexAttribPointer(locations[b"color"], 3, GL_FLOAT, False,
	                      record_len, color_offset)
	
	glMatrixMode(GL_MODELVIEW)
	glPushMatrix()
	glScale(scale, scale, scale)
	glMultMatrixf(m.column_major(q.matrix(rotation)))
	
	offset = 0
	for size in sizes:
		glDrawElements(GL_TRIANGLE_STRIP,
		               size, GL_UNSIGNED_INT,
		               c_void_p(offset))
		offset += size*uint_size
	
	glPopMatrix()


# display ####################################################################

def screen_shot(name="screen_shot.png"):
	"""window screenshot."""
	width, height = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
	size = width*height*3
	
	pixel_buffer = glGenBuffers(1)
	glBindBuffer(GL_PIXEL_PACK_BUFFER, pixel_buffer)
	glBufferData(GL_PIXEL_PACK_BUFFER, size, None, GL_STREAM_READ)
	
	glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE, c_void_p(0))
	data = string_at(glMapBuffer(GL_PIXEL_PACK_BUFFER, GL_READ_ONLY), size)
	
	import png
	png.write(open(name, "wb"), width, height, 3, data)
	
	glUnmapBuffer(GL_PIXEL_PACK_BUFFER)
	glBindBuffer(GL_PIXEL_PACK_BUFFER, 0)
	glDeleteBuffers(1, [pixel_buffer])


def reshape(width, height):
	"""window reshape callback."""
	glViewport(0, 0, width, height)
	
	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	radius = .5 * min(width, height)
	w, h = width/radius, height/radius
	if perspective:
		glFrustum(-w, w, -h, h, 8, 16)
		glTranslate(0, 0, -12)
		glScale(1.5, 1.5, 1.5)
	else:
		glOrtho(-w, w, -h, h, -2, 2)
	
	glMatrixMode(GL_MODELVIEW)
	glLoadIdentity()


def display():
	"""window redisplay callback."""
	glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
	draw_object()
	glutSwapBuffers()


# interaction ################################################################

PERSPECTIVE, LIGHTING, TEXTURING = b'p', b'l', b't'

perspective = False
lighting    = False
texturing   = False

def keyboard(c, x=0, y=0):
	"""keyboard callback."""
	global perspective, lighting, texturing
	
	if c == PERSPECTIVE:
		perspective = not perspective
		reshape(glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT))
	
	elif c == LIGHTING:
		lighting = not lighting
		glUniform1i(locations[b"lighting"], lighting)
	
	elif c == TEXTURING:
		texturing = not texturing
		glUniform1i(locations[b"texturing"], texturing)
		if texturing:
			animate_texture()
	
	elif c == b's':
		screen_shot()
	
	elif c == b'q':
		sys.exit(0)
	glutPostRedisplay()


rotating = False
scaling  = False

rotation = q.quaternion()
scale = 1.

def screen2space(x, y):
	width, height = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
	radius = min(width, height)*scale
	return (2.*x-width)/radius, -(2.*y-height)/radius
	
def mouse(button, state, x, y):
	global rotating, scaling, x0, y0
	if button == GLUT_LEFT_BUTTON:
		rotating = (state == GLUT_DOWN)
	elif button == GLUT_RIGHT_BUTTON:
		scaling = (state == GLUT_DOWN)
	x0, y0 = x, y

def motion(x1, y1):
	global x0, y0, rotation, scale
	if rotating:
		p0 = screen2space(x0, y0)
		p1 = screen2space(x1, y1)
		rotation = q.product(rotation, q.arcball(*p0), q.arcball(*p1))
	if scaling:
		scale *= exp(((x1-x0)-(y1-y0))*.01)
	x0, y0 = x1, y1
	glutPostRedisplay()


# setup ######################################################################

WINDOW_SIZE = 640, 480

def init_glut(argv):
	"""glut initialization."""
	glutInit(argv)
	glutInitWindowSize(*WINDOW_SIZE)
	glutInitDisplayMode(GLUT_RGBA|GLUT_DOUBLE|GLUT_DEPTH)
	
	glutCreateWindow(argv[0].encode())
	
	glutReshapeFunc(reshape)
	glutDisplayFunc(display)
	glutKeyboardFunc(keyboard)
	glutMouseFunc(mouse)
	glutMotionFunc(motion)


def init_opengl():
	# depth test
	glEnable(GL_DEPTH_TEST)
	glDepthFunc(GL_LEQUAL)
	
	# lighting
	light_position = [1., 1., 2., 0.]
	glLight(GL_LIGHT0, GL_POSITION, light_position)
	glMaterialfv(GL_FRONT, GL_SPECULAR, [1., 1., 1., 1.])
	glMaterialf(GL_FRONT, GL_SHININESS, 100.)	
	
	# initial state
	for k in [PERSPECTIVE, LIGHTING, TEXTURING]:
		keyboard(k)


# main #######################################################################

def main(argv=None):
	if argv is None:
		argv = sys.argv
	
	init_glut(argv)
	init_program()
	init_texture()
	init_opengl()
	init_object()
	return glutMainLoop()

if __name__ == "__main__":
	sys.exit(main())
