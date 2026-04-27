import importlib

dbModuleName = "DynamoDB"
dbModulePath = f"db.{dbModuleName}"

dbModule = importlib.import_module(dbModulePath)

class DJDB(getattr(dbModule, dbModuleName)):
    pass
