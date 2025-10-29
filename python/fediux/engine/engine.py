from fediux.utils.logger_util import logger
from fediux.FL.utils.base import BaseModel
from fediux.context import Context

class PythonEngine(BaseModel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.task_code = Context.task_code()

    def run(self):
        if self.task_code:
            # logger.info(globals())
            # logger.info(locals())
            exec(self.task_code, {})
        else:
            raise RuntimeError(f"{self.task_code} empty running code is permitted")



