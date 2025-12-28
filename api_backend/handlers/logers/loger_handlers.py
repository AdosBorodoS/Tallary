import logging

class LogerHandler:
    def __init__(self,logsFilePath, logerName = 'myLoger'):
        self.logerClient = self.__setLogsFormat(logerName, logsFilePath)

    def __setLogsFormat(self, logerName, fileName):
        myLoger = logging.getLogger(logerName)

        if myLoger.handlers:
            return myLoger 
        
        myLoger.setLevel(level=logging.DEBUG)
        
        formatter = logging.Formatter("[%(asctime)s] {%(name)s}  %(levelname)s %(funcName)s(%(lineno)d) - %(message)s")
        
        # Настройка формата логирования в консоль
        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(logging.DEBUG)
        consoleHandler.setFormatter(formatter)
        
        # Настройка формата логирования в файл
        fileLogHandler = logging.FileHandler(filename = fileName, mode='a',encoding="UTF-8")
        fileLogHandler.setFormatter(formatter)
        fileLogHandler.setLevel(logging.INFO)
        
        myLoger.addHandler(consoleHandler)
        myLoger.addHandler(fileLogHandler)
        return myLoger
