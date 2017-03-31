#!/usr/bin/python3
# Copyright (c) 2016-2017, henry232323
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
from contextlib import redirect_stdout
from traceback import format_exc
from inspect import isawaitable
from io import StringIO
import base64
import json

from kyoukai import Kyoukai
from kyoukai.asphalt import HTTPRequestContext, Response
from werkzeug.exceptions import HTTPException


class CmdRunner(object):
    app = Kyoukai("Typheus")

    def __init__(self, bot):
        self.bot = bot

        with open("resources/auth", 'rb') as ath:
            self._key = json.loads(ath.read().decode("utf-8", "replace"))[1]

        with open("resources/sburb.ico", 'rb') as ico:
            self.ico = ico

        @self.app.route("/", methods=["GET"])
        async def index(ctx: HTTPRequestContext):
            try:
                if ctx.request.args['key'] == self._key:
                    return Response(await self.run_cmd(base64.b64decode(ctx.request.args['cmd']).decode()), status=200)
                else:
                    raise HTTPException("Incorrect key", 403)
            except KeyError:
                raise HTTPException("Missing key or command", 400)

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
