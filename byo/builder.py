import logging
import byo.package
import urllib.request
import urllib.parse
import shutil
import shlex
import gpg
import os.path
import byo
from byo.process import Environment
from byo.package import State as PackageState
import multiprocessing

cpu_count = multiprocessing.cpu_count()

logger = logging.getLogger(__name__)


class Builder(object):
	def __init__(self, prefix, target, options):
		self.prefix = prefix
		self.target = target
		self.options = options
		self.metadata = byo.package.read_metadata(target)
		self.gpg = gpg.Context()
		self.root = os.path.join(byo.root, 'build.' + prefix.strip('-'))
		self.archive = None
		self.work_dir = None
		self.env = Environment(self.root, target)
		self.__state_file = os.path.join(self.env.create_dir('packages', self.target), 'state')
		self.__load_state()
		self.__update_vars(self.metadata.data)

	@property
	def state(self):
		return self.__state

	def __load_state(self):
		self.__state = PackageState.NOT_PRESENT
		if not os.path.exists(self.__state_file):
			return
		try:
			with open(self.__state_file) as f:
				self.__state = PackageState[f.read()]
		except:
			logger.exception("failed loading current state")

	def __set_state(self, state):
		self.__state = state
		with open(self.__state_file, "wt") as f:
			f.write(state.name)

	def __update_vars(self, vars):
		vars['Jobs'] = cpu_count
		vars['CrossCompilePrefix'] = self.prefix
		vars['Host'] = self.prefix.rstrip('-')
		vars['InstallDirectory'] = self.env.create_dir('root')
		vars['CCompiler'] = self.prefix + 'gcc'
		vars['Assembler'] = self.prefix + 'as'
		vars['Archiver'] = self.prefix + 'ar'
		vars['Linker'] = self.prefix + 'ld'

	def __fetch_cache(self, url, fname):
		downloads = self.env.create_dir('downloads')
		cached = os.path.join(downloads, fname)
		if os.path.exists(cached):
			return cached

		logger.info('downloading url %s → %s', url, fname)

		with urllib.request.urlopen(url) as response, open(cached, 'wb') as out_file:
			shutil.copyfileobj(response, out_file)

		logger.info('downloading finished')
		return cached

	def _fetch(self):
		url = self.metadata.fetch_url
		if url is None:
			self.__set_state(PackageState.DOWNLOADED)
			return
		parsed = urllib.parse.urlparse(url)
		fname = str(os.path.basename(parsed.path))
		self.archive = self.__fetch_cache(url, fname)
		if self.__state >= PackageState.DOWNLOADED:
			return
		self.__set_state(PackageState.DOWNLOADED)

	def _unpack(self):
		self.work_dir = self.env.create_dir('tmp', self.target, 'work')

		if self.__state >= PackageState.UNPACKED:
			return

		logger.info('unpacking...')
		self.env.exec(self.work_dir, 'tar', '--strip=1', '-xf', self.archive)
		self.__set_state(PackageState.UNPACKED)

	def _build(self):
		if self.__state >= PackageState.BUILT:
			return

		logger.info('building...')
		for cmd in self.metadata.build:
			cmd = shlex.split(cmd)
			self.env.exec(self.work_dir, *cmd)
		self.__set_state(PackageState.BUILT)

	def _install(self):
		if self.__state >= PackageState.INSTALLED:
			return

		logger.info('installing...')
		self.__set_state(PackageState.INSTALLED)

	def _cleanup(self):
		self.env.cleanup()

	def build(self):
		try:
			self._fetch()
			self._unpack()
			self._build()
			self._install()
			self._cleanup()
		except:
			logger.exception('build failed')
			raise


def _build(prefix, target, options):
	logger.info('building %s for %s...' %(target, prefix))
	builder = Builder(prefix, target, options)
	builder.build()

def build(prefix, target, options = {}):
	logger.info('building %s for %s...' %(target, prefix))
	for package in byo.package.get_package_queue(target):
		_build(prefix, package, options)
