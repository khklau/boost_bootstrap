import hashlib
import os
import shutil
import subprocess
import tarfile
import urllib
import zipfile
from waflib import Logs
from waflib.extras.preparation import PreparationContext
from waflib.extras.build_status import BuildStatus
from waflib.extras.filesystem_utils import removeSubdir
from waflib.extras.mirror import MirroredTarFile, MirroredZipFile

__downloadUrl = 'http://sourceforge.net/projects/boost/files/boost/1.54.0/%s/download'
__posixFile = 'boost_1_54_0.tar.gz'
__posixSha256Checksum = '\x41\x2d\x00\x32\x99\xe7\x25\x55\xe1\xe1\xf6\x2f\x51\xd3\xb0\x7e\xca\x2a\x19\x11\xe2\x7c\x44\x2e\xe1\xc0\x81\x67\x82\x6e\xf9\xe2'
__ntFile = 'boost_1_54_0.zip'
__ntSha256Checksum = '\x83\x61\xdd\xef\xbc\x1c\x9c\x2e\x44\x9e\xc9\x4c\xb8\xe0\xda\x66\x49\xd0\x76\x10\x2c\xde\x4e\xa1\x1a\xdf\xdd\x2a\x73\xe8\x41\x1e'
__srcDir = 'src'

def options(optCtx):
    optCtx.load('dep_resolver')
    optCtx.add_option('--variantset', type='string',
	    default='minimal', dest='variantset',
	    help='Build a set of variants, e.g. minimal, complete')
    optCtx.add_option('--toolset', type='string',
	    default='gcc', dest='toolset',
	    help='Compiler toolset, e.g. gcc, msvc')

def prepare(prepCtx):
    prepCtx.options.dep_base_dir = prepCtx.srcnode.find_dir('..').abspath()
    prepCtx.load('dep_resolver')
    status = BuildStatus.init(prepCtx.path.abspath())
    if status.isSuccess():
	prepCtx.msg('Preparation already complete', 'skipping')
	return
    if os.name == 'posix':
	file = MirroredTarFile(
		__posixSha256Checksum,
		__downloadUrl % __posixFile,
		os.path.join(prepCtx.path.abspath(), __posixFile))
    elif os.name == 'nt':
	file = MirroredZipFile(
		__ntSha256Checksum,
		__downloadUrl % __ntFile,
		os.path.join(prepCtx.path.abspath(), __ntFile))
    else:
	prepCtx.fatal('Unsupported OS %s' % os.name)
    prepCtx.msg('Synchronising', file.getSrcUrl())
    if file.sync(10):
	prepCtx.msg('Saved to', file.getTgtPath())
    else:
	prepCtx.fatal('Synchronisation failed')
    extractDir = 'boost_1_54_0'
    removeSubdir(prepCtx.path.abspath(), __srcDir, extractDir, 'bin', 'lib', 'include')
    prepCtx.start_msg('Extracting files to')
    file.extract(prepCtx.path.abspath())
    os.rename(extractDir, __srcDir)
    prepCtx.end_msg(os.path.join(prepCtx.path.abspath(), __srcDir))

def configure(confCtx):
    confCtx.load('dep_resolver')
    status = BuildStatus.init(confCtx.path.abspath())
    if status.isSuccess():
	confCtx.msg('Configuration already complete', 'skipping')
	return
    srcPath = os.path.join(confCtx.path.abspath(), __srcDir)
    os.chdir(srcPath)
    if os.name == 'posix':
	returnCode = subprocess.call([
		os.path.join(srcPath, 'bootstrap.sh'),
		'--prefix=%s' % confCtx.srcnode.abspath()])
    elif os.name == 'nt':
	returnCode = subprocess.call([
		os.path.join(srcPath, 'bootstrap.bat'),
		'--prefix=%s' % confCtx.srcnode.abspath()])
    else:
	confCtx.fatal('Unsupported OS %s' % os.name)
    if returnCode != 0:
	confCtx.fatal('Boost bootstrap failed: %d' % returnCode)

def build(buildCtx):
    status = BuildStatus.load(buildCtx.path.abspath())
    if status.isSuccess():
	Logs.pprint('NORMAL', 'Build already complete                   :', sep='')
	Logs.pprint('GREEN', 'skipping')
	return
    srcPath = os.path.join(buildCtx.path.abspath(), __srcDir)
    os.chdir(srcPath)
    returnCode = subprocess.call([
	    os.path.join(srcPath, 'bjam'),
	    '--prefix=%s' % buildCtx.srcnode.abspath(),
	    '--layout=versioned',
	    '--build-type=%s' % buildCtx.options.variantset,
	    '--toolset=%s' % buildCtx.options.toolset,
	    'install'])
    if returnCode != 0:
	buildCtx.fatal('Boost bjam failed: %d' % returnCode)
    status.setSuccess()
