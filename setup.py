from distutils.core import setup
import py2exe

setup(console=['tradefinder.py'],
  	options = {"py2exe" : {"includes" : "email.mime.text,email.mime.image,email.mime.audio,email.mime.application,email.mime.base,email.mime.message,email.mime.multipart,email.mime.nonmultipart,email.mime.text"}})
