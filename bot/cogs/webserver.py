import os
import json
import subprocess
import time
from flask import Flask, jsonify, request
from discord.ext import commands
from threading import Thread
import asyncio


class Webserver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = Flask(__name__)
        self.setup_routes()
        self.flask_thread = Thread(target=self.run_flask, daemon=True)
        self.flask_thread.start()

    def setup_routes(self):
        @self.app.route('/guild_count')
        def guild_count():
            return jsonify({'guild_count': len(self.bot.guilds)})

        @self.app.route('/guild_info')
        def guild_info():
            guild_id = request.args.get('guild_id')
            if not guild_id or not guild_id.isdigit():
                return jsonify({'success': False, 'error': 'Invalid guild_id'}), 400
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                return jsonify({'success': False, 'error': 'Guild not found'}), 404
            return jsonify({
                'id': guild.id,
                'name': guild.name,
                'icon_url': guild.icon.url if guild.icon else None
            })

        @self.app.route('/status')
        def status():
            return jsonify({
                'status': 'online',
                'guilds': len(self.bot.guilds),
                'users': len(self.bot.users),
                'latency': round(self.bot.latency * 1000)
            })

    def run_flask(self):
        self.app.run(host='0.0.0.0', port=5000)


async def setup(bot):
    await bot.add_cog(Webserver(bot))
