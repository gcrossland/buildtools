# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#  SCons Utility Library
#  © Geoff Crossland 2014-2017
# ------------------------------------------------------------------------------
from SCons.Script import *
from SCons.Errors import UserError
import re
import os
os_ = os
import shutil
import sys
import platform
import SCons.Util
import SCons.Subst

def _listDir (path, leafNamePattern):
  if isinstance(leafNamePattern, basestring):
    leafNamePattern = re.compile(leafNamePattern, re.DOTALL)
  for leafName in os.listdir(path):
    if leafNamePattern.match(leafName) is not None:
      yield leafName

class _DependeeList (object):
  def __init__ (self, env, dependees = None):
    self._libCachePathName = os.path.join(env['libCacheDir'], env['fullconfig'])
    self._dependees = []
    self._dependeeSet = {}

    if dependees is not None:
      for dependee in dependees:
        self.add(dependee)

  @staticmethod
  def _getName (name, maj, min = None):
    r = name + "-" + str(maj)
    if min is not None:
      r += "." + str(min)
    return r

  def _listLibCacheLibDirs (self, name, maj):
    if not os.path.exists(self._libCachePathName):
      return ()
    return list(_listDir(self._libCachePathName, "^" + re.escape(_DependeeList._getName(name, maj, "")) + "[0-9]+$"))

  def add (self, earliestDependee):
    (name, maj, min) = earliestDependee
    t = self._listLibCacheLibDirs(name, maj)
    if len(t) > 1:
      raise UserError("There are multiple builds for " + _DependeeList._getName(name, maj, "x") + " in " + self._libCachePathName + ".")
    if len(t) == 0:
      foundMin = -1
    else:
      leafName = t[0]
      try:
        foundMin = int(leafName[leafName.rfind('.') + 1:])
      except:
        raise UserError(leafName + " is not a valid lib cache lib directory name.")
    if foundMin < min:
      raise UserError("There are no builds for " + _DependeeList._getName(name, maj, min) + " or later in " + self._libCachePathName + ".")

    self._add((name, maj, foundMin))

  def _add (self, dependee):
    name = dependee[0]
    prevDependee = self._dependeeSet.get(name, None)
    if prevDependee is not None and prevDependee != dependee:
      raise UserError(_DependeeList._getName(*dependee) + " is available, but " + _DependeeList._getName(*prevDependee) + " is also required.")

    self._dependees.append(dependee)
    self._dependeeSet[name] = dependee

  def addList (self, list):
    assert self._libCachePathName == list._libCachePathName
    for dependee in list._dependees:
      self._add(dependee)

  def __len__ (self):
    return len(self._dependees)

  def __getitem__ (self, k):
    return self._dependees[k]

  def getLibCacheLibDirPathNames (self, sub):
    return (os.path.join(self._libCachePathName, _DependeeList._getName(*dependee), sub) for dependee in self._dependees)

  INCLUDE = "include"
  LIB = "lib"

  def prepareLibCacheLibDir (self, name, maj, min):
    for oldLibDir in self._listLibCacheLibDirs(name, maj):
      shutil.rmtree(os.path.join(self._libCachePathName, oldLibDir))

    return os.path.join(self._libCachePathName, _DependeeList._getName(name, maj, min))

def _getEnvDependeeList (env):
  if '_dependeeList' in env:
    return env['_dependeeList']
  else:
    env['_dependeeList'] = l = _DependeeList(env)
    return l

_timeInt = None

def _getTimeInt ():
  global _timeInt
  if _timeInt is None:
    import time
    t = time.gmtime()
    i = t.tm_year
    i = i * 100 + t.tm_mon
    i = i * 100 + t.tm_mday
    i = i * 100 + t.tm_hour
    i = i * 100 + t.tm_min
    i = i * 100 + t.tm_sec
    _timeInt = i
  return _timeInt

##
# Builds the C++ library of the given name (based on the corresponding source
# files), ensuring that the listed dependencies are fulfilled. extraFn specifies
# a function, with arguments env and the value to be used for CPPPATH, to
# request to build any extra needed object files; it returns a tuple of a node
# list of new objects and a node list of extra header files to be included in
# the deployment set. If maj != -1, the library is marked as being the specified
# version and is deployed to LIBCACHEDIR; otherwise, it is only available for
# the local application.
# TODO only require the direct dependees (and not in any order)
def Lib (env, name, maj, min, dependees = None, extraFn = None):
  if maj != -1 and min == -1:
    min = _getTimeInt()

  dependeeList = _DependeeList(env, dependees)
  _getEnvDependeeList(env).addList(dependeeList)

  objs = []
  hdrs = []

  cpppath = list(dependeeList.getLibCacheLibDirPathNames(_DependeeList.INCLUDE))
  dependenciesExpr = ""
  if maj != -1:
    # TODO put lib version in a seperate object file
    dependenciesExpr += "_version_(" + name + "," + str(maj) + "," + str(min) + ")"
    dependenciesExpr += "".join("_dependson_(" + name + "," + str(maj) + "," + str(min) + ")" for name, maj, min in dependeeList)
  objs.extend(env.StaticObject("libraries/" + name + ".cpp", CPPPATH = cpppath, CPPDEFINES = dict(env['CPPDEFINES'], LIB_DEPENDENCIES = dependenciesExpr)))
  objs.extend(env.StaticObject(env.Glob("libraries/" + name + "_*.cpp"), CPPPATH = cpppath))
  if maj != -1:
    hdrs.extend(env.Glob("libraries/" + name + ".hpp"))
    hdrs.extend(env.Glob("libraries/" + name + ".ipp"))
    hdrs.extend(env.Glob("libraries/" + name + "_*.hpp"))
    hdrs.extend(env.Glob("libraries/" + name + "_*.ipp"))

  if extraFn:
    extraObjs, extraHdrs = extraFn(env, cpppath)
    objs.extend(extraObjs)
    if maj != -1:
      hdrs.extend(extraHdrs)

  if maj != -1:
    libs = env.StaticLibrary(name, objs)

    libCacheLibDirPathName = dependeeList.prepareLibCacheLibDir(name, maj, min)
    env.Default(env.Install(os.path.join(libCacheLibDirPathName, _DependeeList.LIB), libs))
    env.Default(env.Install(os.path.join(libCacheLibDirPathName, _DependeeList.INCLUDE), hdrs))

  return objs

##
# Builds the C++ application binary of the given name (based on the source files
# in the dir), ensuring that the listed dependencies are fulfilled.
def App (env, name, libObjs, dependees = None, extraFn = None):
  dependeeList = _DependeeList(env, dependees)
  dependeeList.addList(_getEnvDependeeList(env))

  objs = list(libObjs)

  cpppath = list(dependeeList.getLibCacheLibDirPathNames(_DependeeList.INCLUDE))
  objs.extend(env.StaticObject(env.Glob("*.cpp"), CPPPATH = cpppath))

  outputs = env.Program(name, objs, LIBS = [name for name, maj, min in reversed(dependeeList)] + env['LIBS'], LIBPATH = list(dependeeList.getLibCacheLibDirPathNames(_DependeeList.LIB)))
  env.Default(env.Install("#", outputs))

  return outputs

##
# Utility to build a lib (with Lib()) and its corresponding application binary
# (with App()).
def LibAndApp (env, name, maj, min, dependees, extraFn = None, appDependees = None, appExtraFn = None):
  return env.App(name, env.Lib(name, maj, min, dependees, extraFn), appDependees, appExtraFn)

##
# Creates a variant tree (with VariantDir()) and then calls the given function
# while in the root of that tree (in the same way that SConscript(variant_dir)
# runs statements from a subsidiary file in the root of that tree).
def InVariantDir (env, variantDir, srcDir, fn):
  if isinstance(variantDir, basestring):
    variantDir = env.Dir(variantDir)

  env.VariantDir(variantDir, srcDir, duplicate = 0)
  prevCwd = env.fs.getcwd()
  env.fs.chdir(variantDir, change_os_dir = 0)
  try:
    return fn(env)
  finally:
    env.fs.chdir(prevCwd, change_os_dir = 0)

def _mapByPrefix (keyPrefixee, mappings):
  for k, v in mappings:
    if keyPrefixee.startswith(k):
      return v
  return None

def _bits (arch):
  if arch.endswith('_32'):
    return 32
  if arch.endswith('_64'):
    return 64
  assert False

class _SyntaxError (UserError):
  SUFFIX = "\nSyntax: scons CONFIG=release|debug|debugopt [LIBCACHEDIR=<path>] [OS=riscos|win32|posix] [ARCH=[arm]|[x86]_[32]|[64]] TOOL_GCC=<bin dir path> [...]"

  def __init__ (self, msg):
    UserError.__init__(self, msg + _SyntaxError.SUFFIX)

class _ArgError (_SyntaxError):
  def __init__ (self, *a):
    assert len(a) % 2 == 0
    assert len(a) >= 2

    if a[1] is None:
      msg = a[0] + " must be specified"
    else:
      msg = "'" + str(a[1]) + "' is not a valid value for " + a[0]
    if len(a) != 2:
      msg += " when "
      for i in xrange(2, len(a), 2):
        if i == 2:
          pass
        elif len(a) - 2:
          msg += " and "
        else:
          msg += ", "
        msg += a[i] + " is "
        v = a[i + 1]
        if v is None:
          msg += "not specified"
        else:
          msg += "'" + str(v) + "'"
    msg += "."

    _SyntaxError.__init__(self, msg)

##
# Returns a construction environment (which may or may not be the default)
# initialised according to the variables specified on the command line. It
# includes sconsutils' extra construction variables (hostOs, hostArch, config,
# libCacheDir, os, arch, tool and oDir), pseudo-Builders (Lib(), App() and
# LibAndApp()) and construction environment methods (InVariantDir()).
def getEnv ():
  hostOs = _mapByPrefix(sys.platform, (
    ("riscos", 'riscos'),
    ("win32", 'win32'),
    ("linux", 'posix'),
    ("cygwin", 'posix'),
    ("sunos", 'posix'),
    ("darwin", 'posix'),
    ("freebsd", 'posix')
  ))
  if hostOs is None:
    raise UserError("'" + sys.platform + "' is an unknown platform.")

  hostArch = _mapByPrefix(platform.machine().lower(), (
    ("aarch64", 'arm_64'),
    ("armv", 'arm_32'),
    ("x86_64", 'x86_64'),
    ("amd64", 'x86_64'),
    ("x86", 'x86_32'),
    ("i386", 'x86_32'),
    ("i486", 'x86_32'),
    ("i586", 'x86_32'),
    ("i686", 'x86_32')
  ))
  if hostArch is None:
    raise UserError("'" + platform.machine() + "' is an unknown architecture.")

  constructionVars = dict(
    hostOs = hostOs,
    hostArch = hostArch
  )

  config = ARGUMENTS.get('CONFIG', None)
  if config in ('release', 'debug', 'debugopt'): # TODO 'prof', 'cppcheck'
    libCacheDir = ARGUMENTS.get('LIBCACHEDIR', None)
    if libCacheDir is None:
      libCacheDir = os_.path.join(os_.path.dirname(__file__), "cache")
      print "LIBCACHEDIR not specified; using " + libCacheDir
    libCacheDir = os_.path.abspath(libCacheDir)

    arch = ARGUMENTS.get('ARCH', None)
    if arch is None:
      arch = hostArch
      print "ARCH not specified; using " + arch
    if arch in ('arm_32', 'arm_64', 'x86_32', 'x86_64'):
      pass
    else:
      raise _ArgError('ARCH', arch, 'CONFIG', config)

    os = ARGUMENTS.get('OS', None)
    if os is None:
      os = hostOs
      print "OS not specified; using " + os
    if os in ('riscos',):
      if arch not in ('arm_32',):
        raise _ArgError('ARCH', arch, 'OS', os, 'CONFIG', config)
    elif os in ('win32', 'posix'):
      pass
    else:
      raise _ArgError('OS', os, 'CONFIG', config)

    constructionVars.update(
      config = config,
      libCacheDir = libCacheDir,
      os = os,
      arch = arch,
      fullconfig = config + "-" + os + "-" + arch,
      tools = [],
      ENV = {'PATH': []},
      TARGET_OS = {'riscos': None, 'win32': "win32", 'posix': None}[os],
      TARGET_ARCH = {'arm_32': None, 'arm_64': None, 'x86_32': "x86", 'x86_64': "x86_64"}[arch],
      CPPDEFINES = {'OS_' + os.upper(): None, 'ARCH_' + arch.upper(): None},
      CXXFLAGS = [],
      LIBS = [],
      LINKFLAGS = []
    )

    toolGcc = ARGUMENTS.get('TOOL_GCC', None)
    if toolGcc is not None:
      constructionVars['tool'] = 'gcc'
      if os in ('win32',):
        constructionVars['tools'].append('mingw')
      else:
        constructionVars['tools'].extend(('g++', 'gnulink', 'ar', 'gas'))
      constructionVars['ENV']['PATH'].append(toolGcc)

      # TODO consider -std=c++11, -Wno-type-limits, -Wall -Wextra
      constructionVars['CXXFLAGS'].extend(("-std=gnu++11", "-ftemplate-backtrace-limit=0", "-Wno-conversion", "-Wsign-conversion", "-Wsign-compare", "-Wctor-dtor-privacy", "-Wnon-virtual-dtor", "-Wreorder", "-Wold-style-cast", "-Woverloaded-virtual", "-Wchar-subscripts", "-Wformat", "-Wmissing-braces", "-Wparentheses", "-Wsequence-point", "-Wreturn-type", "-Wunused-variable", "-Wstrict-aliasing", "-Wstrict-overflow", "-Wextra", "-Wfloat-equal", "-Wpointer-arith", "-Waddress", "-Wmissing-field-initializers", "-Winvalid-pch", "-Wdisabled-optimization", "-Wno-non-template-friend"))
      constructionVars['LINKFLAGS'].append("-Wl,--demangle")

      if config in ('release',):
        constructionVars['CPPDEFINES']['NDEBUG'] = None
        constructionVars['CXXFLAGS'].extend(("-g0", "-fno-lto", "-O3"))
        # TODO consider -march, -mtune
      if config in ('debug',):
        constructionVars['CXXFLAGS'].extend(("-g3", "-gdwarf-2", "-fno-omit-frame-pointer", "-fno-lto", "-O0"))
      if config in ('debugopt',):
        constructionVars['CXXFLAGS'].extend(("-g3", "-gdwarf-2", "-fno-omit-frame-pointer", "-fno-lto", "-O3", "-march=native", "-mtune=native"))

      if os in ('riscos',):
        constructionVars['CXXFLAGS'].append("-mapcs-32")
      if os in ('win32',):
        constructionVars['LINKFLAGS'].append("-static")
      if os in ('posix',):
        constructionVars['LIBS'].extend(("pthread", "stdc++"))
        constructionVars['LINKFLAGS'].extend(("-static-libstdc++", "-Wl,--as-needed"))

      if arch in ('arm_32',):
        constructionVars['CXXFLAGS'].append("-march=armv3")
      if arch in ('arm_64',):
        constructionVars['CXXFLAGS'].append("-march=armv8-a")
      if arch in ('x86_32', 'x86_64'):
        constructionVars['CXXFLAGS'].append("-m" + str(_bits(arch)))

    toolClang = None

    if toolGcc is None and toolClang is None:
      raise _SyntaxError("No tool specified.")
  elif config in (): # TODO 'doc'
    pass
  else:
    raise _ArgError('CONFIG', config)

  if hostOs in ('win32',):
    # Since we're explicitly setting ENV, ensure that we manually set the mandatory
    # environment variables (see SCons.Platform.win32.generate()).
    for k in ('SystemDrive', 'SystemRoot', 'TEMP', 'TMP', 'COMSPEC'):
      if k in os_.environ:
        constructionVars['ENV'][k] = os_.environ[k]
    constructionVars['ENV']['PATH'].append(constructionVars['ENV']['SystemRoot'] + "\\System32")
    constructionVars['ENV']['PATHEXT'] = ".COM;.EXE;.BAT;.CMD"

    # Work around subprocess.Popen using PATH from this process' environment and not
    # from the supplied env (see https://bugs.python.org/issue15451).
    for k in ('PATH',):
      v = constructionVars['ENV'][k]
      # (cf. SCons.Action._subproc())
      if isinstance(v, list):
        strV = os_.pathsep.join(str(o) for o in SCons.Util.flatten_sequence(v))
      else:
        strV = str(v)
      os_.environ[k] = strV

  if hostOs in ('posix',):
    # Ensure that the shell's full path is available.
    constructionVars['SHELL'] = "/bin/sh"

    # Ensure that shell escaping is done properly (see
    # http://scons.tigris.org/issues/show_bug.cgi?id=2766).
    def _escape(arg):
        slash = '\\'
        special = '"$`'

        arg = arg.replace(slash, slash+slash)
        for c in special:
            arg = arg.replace(c, slash+c)

        return '"' + arg + '"'
    constructionVars['ESCAPE'] = _escape

    # Ensure that shell string escaping (e.g. for single arguments which represent
    # an entire command line) is performed in more cases (which might be too many
    # cases, but we'll cross that bridge when we come to it).
    def _is_literal(self):
        return self.literal is None or self.literal
    SCons.Subst.CmdStringHolder.is_literal = _is_literal

  env = DefaultEnvironment(**constructionVars)
  env.EnsureSConsVersion(2, 1, 0)
  env['fullconfig'] += "-" + env['tool'] + env.get('CXXVERSION', "")
  env['oDir'] = "#o/" + env['fullconfig']
  env.Decider('MD5-timestamp')
  env.SConsignFile(os_.path.abspath(os_.path.join("o", ".sconsign")))
  env.AddMethod(Lib)
  env.AddMethod(App)
  env.AddMethod(LibAndApp)
  env.AddMethod(InVariantDir)
  #print env.Dump()

  return env
