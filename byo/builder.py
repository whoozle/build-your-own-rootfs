import logging
import byo.package
import urllib.request
import urllib.parse
import shutil
import shlex
#import gpg
import os.path
import byo
from byo.process import Environment
from byo.package import State, PackageState
import multiprocessing
import sys

cpu_count = multiprocessing.cpu_count()

logger = logging.getLogger(__name__)

def get_file_tags(path): #fixme: put into base package script
	if path.startswith('boot'):
		return ('boot', )
	if path.startswith('usr/include') \
		or path.startswith('usr/man') \
		or path.endswith('Makefile') \
		or path.startswith('usr/share/man') \
		or path.startswith('usr/share/doc') \
		or path.startswith('usr/lib/pkgconfig') \
		or path.startswith('etc/portage') \
		or (path.startswith('usr/bin') and path.endswith('-config')) \
		or path.endswith('.a'):
		return ('devel', )
	else:
		return ('core', )


class Builder(object):
	def __init__(self, prefix, target, options):
		self.prefix = prefix
		self.target = target
		self.options = options
		self.metadata = byo.package.read_metadata(target)
		#self.gpg = gpg.Context()
		self.root = os.path.join(byo.root, 'build.' + prefix.strip('-'))
		self.archive = None
		self.env = Environment(self.root, target)

		self.__force = options.get('force', False)
		self.__keep = options.get('keep', False)
		if self.__force:
			self.env.cleanup()

		self.packages_dir = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'packages')
		self.root_dir = self.env.create_dir('root')
		self.work_dir = self.env.create_dir('tmp', self.target, 'work')

		self.__update_vars(self.metadata.data)
		install_dir = self.metadata.install_dir
		if install_dir: #custom installation directory, e.g. busybox _install
			logger.debug('custom install directory %s', install_dir)
			if not os.path.isabs(install_dir): #prepend work directory if it's not absolute
				install_dir = os.path.join(self.work_dir, install_dir)
		else:
			install_dir = self.env.create_dir('tmp', self.target, 'root')

		self.install_dir = install_dir
		self.__state = PackageState(self.env.create_dir('packages', self.target))
		if self.__force:
			self.__state.reset()
		self.metadata.data['InstallDirectory'] = self.install_dir

	def __update_vars(self, vars):
		vars['Jobs'] = cpu_count
		vars['CrossCompilePrefix'] = self.prefix
		linux_platforms = (('aarch64', 'arm64'), ('arm', 'arm'), ('mips', 'mips'), ('x86_64', 'x84_64'))
		for name, platform in linux_platforms:
			if name in self.prefix:
				vars['LinuxPlatform'] = platform
				break
		vars['Host'] = self.prefix.rstrip('-')
		vars['TargetRoot'] = self.root_dir
		vars['TargetDevelopmentRoot'] = self.root_dir
		vars['WorkDirectory'] = self.work_dir
		vars['AuxFilesDirectory'] = os.path.join(self.packages_dir, self.target + ".files")
		c_compiler = self.prefix + 'gcc'
		vars['SystemRootDirectory'] = self.env.get_output(self.work_dir, c_compiler, '-print-sysroot').strip()
		vars['CCompiler'] = c_compiler
		vars['CXXCompiler'] = self.prefix + 'g++'
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
			self.__state.state = State.DOWNLOADED
			return
		parsed = urllib.parse.urlparse(url)
		fname = str(os.path.basename(parsed.path))
		self.archive = self.__fetch_cache(url, fname)
		if self.__state.state >= State.DOWNLOADED:
			return
		self.__state.state = State.DOWNLOADED

	def _unpack(self):
		if self.__state.state >= State.UNPACKED:
			return

		if self.archive:
			logger.info('unpacking...')
			self.env.exec(self.work_dir, 'tar', '--strip=1', '-xf', self.archive)
		self.__state.state = State.UNPACKED

	def _build(self):
		if self.__state.state >= State.BUILT:
			return

		logger.info('building...')
		for cmd in self.metadata.build:
			cmd = shlex.split(cmd)
			self.env.exec(self.work_dir, *cmd)
		self.__state.state = State.BUILT

	def __link(self, dst_dir, src_dir, file, warn_overwrite = True):
		src_file = os.path.join(src_dir, file)
		dst_file = os.path.join(dst_dir, file)
		real_dst_dir = os.path.dirname(dst_file)
		if os.path.exists(dst_file) or os.path.islink(dst_file):
			if warn_overwrite:
				logger.warn('overwriting %s', dst_file)
			os.unlink(dst_file)
		if not os.path.exists(real_dst_dir):
			os.makedirs(real_dst_dir)

		if os.path.islink(src_file):
			linkto = os.readlink(src_file)
			os.symlink(linkto, dst_file)
		else:
			try:
				os.link(src_file, dst_file)
			except OSError as e:
				if e.errno == 18: #x-device link
					try:
						shutil.copy(src_file, dst_file)
					except FileNotFoundError:
						logger.warn('skipping broken symlink at %s', file)
				else:
					raise


	def _install(self):
		if self.__state.state >= State.INSTALLED:
			return

		copy_to_root = self.metadata.copy_to_root
		logger.info('installing...')
		registry = {}
		for src_dir, src_dirs, files in os.walk(self.install_dir, topdown = True):
			dirname = os.path.relpath(src_dir, self.install_dir)
			dst_dir = os.path.join(self.root_dir, dirname)
			self.env.create_dir(dst_dir)
			for file in files:
				fullname = os.path.join(dirname, file)
				tags = get_file_tags(fullname)
				for tag in tags:
					registry_files = registry.setdefault(tag, [])
					registry_files.append(fullname)

				if copy_to_root:
					logger.debug("installing %s %s", fullname, tags)
					self.__link(dst_dir, src_dir, file)

		self.__state.files = registry
		self.__state.state = State.INSTALLED

	def _cleanup(self):
		if not self.__keep:
			self.env.cleanup()

	def _extract(self):
		extract = self.options.get('extract', [])
		if not extract:
			return

		logger.debug('extract tags %s', extract)
		dst_dir = self.env.create_dir('root.' + '+'.join(extract))
		logger.debug('extract to %s', dst_dir)

		copy_to_root = self.metadata.copy_to_root
		src_dir = self.root_dir if copy_to_root else self.install_dir
		logger.debug('extracting from %s', src_dir)
		for tag in extract:
			files = self.__state.files
			tagged = files.get(tag, [])
			for file in tagged:
				logger.debug("extracting %s", file)
				self.__link(dst_dir, src_dir, file, warn_overwrite = False)
				if tag == 'core':
					try:
						self.env.exec(self.root, self.prefix + 'strip', '--strip-unneeded', os.path.join(dst_dir, file))
					except:
						pass

	def build(self):
		try:
			self._fetch()
			self._unpack()
			self._build()
			self._install()
			self._extract()
			self._cleanup()
		except:
			logger.exception('build failed')
			raise


def _build(prefix, target, **options):
	logger.info('building %s for %s...' %(target, prefix))
	logger.debug('package options %s', options)
	builder = Builder(prefix, target, options)
	builder.build()

def build(prefix, *targets, **options):
	global_options = {}
	global_options['extract'] = options['extract']
	logger.debug('options %s', options)

	for target in targets:
		for package in byo.package.get_package_queue(target):
			_build(prefix, package, ** (options if target == package else global_options))
