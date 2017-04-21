#!/usr/bin/env python3
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
import io
import os
import sys
import psutil
import asyncio
import discord
from textwrap import indent
from contextlib import redirect_stdout
from traceback import format_exc, print_exc
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
        self._last_result = None

        with open("resources/auth", 'rb') as ath:
            self._auth = json.loads(ath.read().decode("utf-8", "replace"))
            self._key = self._auth[1]

        with open("resources/sburb.ico", 'rb') as ico:
            self.ico = ico

        @self.app.route("/", methods=["GET"])
        async def index(ctx: HTTPRequestContext):
            try:
                if ctx.request.args['key'] == self._key:
                    return Response(await self.run_cmd(base64.b64decode(ctx.request.args['cmd']).decode()), status=200)
                else:
                    raise HTTPException("Incorrect key", Response(status=403))

            except KeyError:
                raise HTTPException("Missing key or command", Response(status=400))

        @self.app.route("/servers/<int:snowflake>/", methods=["GET"])
        async def getservinfo(ctx: HTTPRequestContext, snowflake: int):
            try:
                return Response(await self.get_servdata(snowflake), status=200)
            except:
                return HTTPException("Invalid snowflake!", Response(status=400))

        @self.app.route("/users/<int:snowflake>/", methods=["GET"])
        async def getuserinfo(ctx: HTTPRequestContext, snowflake: int):
            try:
                return Response(await self.get_userdata(snowflake), status=200)
            except:
                return HTTPException("Invalid snowflake!", Response("Failed to fetch info!", status=400))

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code. Borrowed from RoboDanny"""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    def get_syntax_error(self, e):
        if e.text is None:
            return '\n{0.__class__.__name__}: {0}\n'.format(e)
        return '\n{0.text}{1:>{0.offset}}\n{2}: {0}'.format(e, '^', type(e).__name__)

    async def run_cmd(self, msg):
        msg = msg.replace("\\n", "\n")

        env = {
            'bot': self.bot,
            '_': self._last_result
        }

        env.update(globals())

        body = self.cleanup_code(msg)
        stdout = io.StringIO()

        to_compile = 'async def func():\n%s' % indent(body, '  ')

        try:
            exec(to_compile, env)
        except SyntaxError as e:
            return self.get_syntax_error(e)

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            return '\n{}{}\n'.format(value, format_exc())
        else:
            value = stdout.getvalue()

            if ret is None:
                if value:
                    return '\n%s\n' % value
            else:
                self._last_result = ret
                return '\n%s%s\n' % (value, ret)

    async def get_userdata(self, snowflake):
        request = """SELECT info FROM userdata WHERE UUID = {}""".format(snowflake)
        values = await self.bot.conn.fetch(request)
        try:
            data = dict(snowflake=snowflake, info=json.loads(values[0]["info"]))
            return json.dumps(data, indent=4)
        except:
            print_exc()
            return json.dumps(dict(error="User not found!"))

    async def get_servdata(self, snowflake):
        request = """SELECT info FROM servdata WHERE UUID = {}""".format(snowflake)
        values = await self.bot.conn.fetch(request)
        try:
            data = dict(snowflake=snowflake, info=json.loads(values[0]["info"]))
            return json.dumps(data, indent=4)
        except:
            print_exc()
            return json.dumps(dict(error="Server not found!"))
