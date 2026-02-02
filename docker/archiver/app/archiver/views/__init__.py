import pkgutil
for imp, module, ispackage in pkgutil.walk_packages(__path__, __name__+'.'):
  __import__(module)