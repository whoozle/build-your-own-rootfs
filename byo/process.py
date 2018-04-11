import logging
import os
import subprocess
import shutil

logger = logging.getLogger(__name__)

class Environment(object):
	def __init__(self, root, name):
		self.root = root
		self.name = name
		self.log_dir = self.create_dir('tmp', name)
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
		if cwd is None:
			raise Exception("you must provide current directory for your command")

		env = os.environ.copy()

		mod_args = []
		can_be_var = True
		for arg in args:
			if can_be_var and '=' in arg: #var
				pos = arg.index('=')
				key, value = arg[:pos], arg[pos + 1:]
				logger.debug('setting %s to %s' %(key, value))
				env[key] = value
			else:
				can_be_var = False
				mod_args.append(arg)

		args = mod_args
		cmd = " ".join(args)
		logger.debug("running %s", cmd)
		with open(self.log_path, "at") as log:
			log.write("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nrunning %s\n" %cmd)
			completed = subprocess.run(args, stderr = subprocess.STDOUT, stdout = log, bufsize = 256 * 1024, cwd = cwd, env = env)
			if completed.returncode != 0:
				raise Exception("command %s failed, cwd: %s" %(cmd, cwd))

	def cleanup(self):
		tmp = os.path.join(self.root, 'tmp', self.name)
		if os.path.exists(tmp):
			logger.info('cleaning up...')
			shutil.rmtree(tmp)
			logger.info('all done')
