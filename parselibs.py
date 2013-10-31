# -*- coding: iso-8859-1 -*-
import sys



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

def action_libnames (list):
  print " ".join((name for name, maj, min in list))

def action_dependenciesdefn (list):
  print "static const bool DEPENDSON = (" + "".join(("dependson(" + name + "," + str(maj) + "," + str(min) + ")," for name, maj, min in list)) + "true);"



if __name__ == "__main__":
  main([arg.decode(sys.stdin.encoding) for arg in sys.argv[1:]])
