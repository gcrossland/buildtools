# -*- coding: iso-8859-1 -*-
import sys



def main (args):
  syntax = "Syntax: parselibs.py <action> [<lib name> <version>] ..."
  if len(args) < 1:
    sys.exit(syntax)
  action = args[0]
  args = args[1:]
  if len(args) % 2 != 0:
    sys.exit(syntax)
  dependees = []
  i = 0
  while i != len(args):
    libName = args[i]
    versionStr = args[i + 1]

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

    dependees.append((libName, versionMaj, versionMin))
    i += 2

  actionFn = eval("action_" + action)
  actionFn(dependees)

def action_dependenciesdefn (list):
  print "static const bool DEPENDSON = (" + "".join(("dependson(" + name + "," + str(maj) + "," + str(min) + ")," for name, maj, min in list)) + "true);"

def action_libdirs (list):
  print " ".join((name.lower() + "-" + str(maj) + "." + str(min) for name, maj, min in list))

def action_libnames (list):
  print " ".join((name.lower() for name, maj, min in list))



if __name__ == "__main__":
  main([arg.decode(sys.stdin.encoding) for arg in sys.argv[1:]])
