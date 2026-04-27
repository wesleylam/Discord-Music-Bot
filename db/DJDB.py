import importlib
from const.config import db_backend

dbModuleName = db_backend
dbModulePath = f"db.{dbModuleName}"

dbModule = importlib.import_module(dbModulePath)

class DJDB(getattr(dbModule, dbModuleName)):
    pass
