import logging
import os
import subprocess

logger = logging.getLogger(__name__)

class Environment(object):
	def __init__(self, root, name):
		self.root = root
		self.name = name
		self.log_dir = self.create_dir("log")
		self.log_path = os.path.join(self.log_dir, "build.log")
		with open(self.log_path, "wt") as log:
			pass

	def create_dir(self, *args):
		path = os.path.join(self.root, *args)
		try:
			os.makedirs(path)
		except:
			pass
		return path

	def exec(self, cwd, *args, **kw):
		cmd = " ".join(args)
		logger.debug("running %s", cmd)
		with open(self.log_path, "at") as log:
			log.write("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nrunning %s\n" %cmd)
			pipe = subprocess.run(args, stderr = subprocess.STDOUT, stdout = log, bufsize = 256 * 1024, cwd = cwd)
