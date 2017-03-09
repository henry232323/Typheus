from contextlib import redirect_stdout
from traceback import format_exc
from inspect import isawaitable
from io import StringIO
import base64
from sanic import Sanic
from sanic.response import text, file
from sanic.exceptions import ServerError
import json

class CmdRunner():
    app = Sanic(__name__)

    def __init__(self, bot):
        self.bot = bot

        with open("resources/auth", 'rb') as ath:
            self._key = json.loads(ath.read().decode("utf-8", "replace"))[1]

        with open("resources/sburb.ico", 'rb') as ico:
            self.ico = ico

        @self.app.route("/")
        async def command(request):
            try:
                if request.args['key'][0] == self._key:
                    return text(await self.run_cmd(base64.b64decode(request.args['cmd'][0]).decode()))
                else:
                    raise ServerError("Incorrect key")
            except KeyError:
                raise ServerError("Missing key or command")

        @self.app.route("/favicon.ico")
        async def favicon(request):
            return file(self.ico)

    async def run_cmd(self, msg):
        request_handler = self
        self = self.bot
        msg = msg.replace("\\n", "\n")
        executor = exec
        if msg.count('\n') == 0:
            # single statement, potentially 'eval'
            try:
                code = compile(msg, '<repl>', 'eval')
            except SyntaxError:
                pass
            else:
                executor = eval

        if executor is exec:
            try:
                code = compile(msg, '<repl>', 'exec')
            except SyntaxError as e:
                return str(e)

        fmt = None
        stdout = StringIO()

        try:
            with redirect_stdout(stdout):
                result = executor(code)
                if isawaitable(result):
                    result = await result

        except Exception as e:
            value = stdout.getvalue()
            fmt = '{}{}'.format(value, format_exc())
        else:
            value = stdout.getvalue()
            if result is not None:
                fmt = '{}{}'.format(value, result)
            elif value:
                fmt = '{}'.format(value)

        if fmt is not None:
            return fmt
