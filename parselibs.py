# -*- coding: iso-8859-1 -*-
import sys
import os
import os.path
import glob



def main (args):
  syntax = "Syntax: parselibs.py <action> [<libname-maj.min>] ..."
  if len(args) < 1:
    sys.exit(syntax)
  action = args[0]
  dependees = []
  for s in args[1:]:
    dash = s.find('-')
    if dash == -1:
      sys.exit(syntax)
    name = s[:dash]
    versionStr = s[dash + 1:]
    dot = versionStr.find('.')
    if dot == -1:
      sys.exit(syntax)
    versionMajStr = versionStr[:dot]
    versionMinStr = versionStr[dot + 1:]
    try:
      versionMaj = int(versionMajStr)
      versionMin = int(versionMinStr)
    except:
      sys.exit(syntax)
    dependees.append((name, versionMaj, versionMin))
  actionFn = eval("action_" + action)
  actionFn(dependees)

def action_availablelibs (list):
  libCacheDir = os.environ.get('LIBCACHEDIR', None)
  if not libCacheDir:
    sys.exit("LIBCACHEDIR is not available")

  for i in xrange(0, len(list)):
    (name, maj, min) = list[i]
    t = glob.glob(os.path.join(libCacheDir, name + "-" + str(maj) + ".*"))
    if len(t) != 1:
      sys.exit("There are " + {True: "no", False: "multiple"}[len(t) == 0] + " builds for " + name + "-" + str(maj) + ".x")
    leafName = os.path.split(t[0])[1]
    try:
      foundMin = int(leafName[leafName.rfind('.') + 1:])
    except:
      sys.exit(leafName + " is not a valid build directory name")
    if foundMin < min:
      sys.exit(leafName + " is available, but is too old a version")
    list[i] = (name, maj, foundMin)

  print " ".join((name + "-" + str(maj) + "." + str(min) for name, maj, min in list))

def action_libnames (list):
  print " ".join((name for name, maj, min in list))

def action_dependenciesdefn (list):
  print "static const bool DEPENDSON = (" + "".join(("_dependson_(" + name + "," + str(maj) + "," + str(min) + ")," for name, maj, min in list)) + "true);"



if __name__ == "__main__":
  main([arg.decode(sys.stdin.encoding) for arg in sys.argv[1:]])
