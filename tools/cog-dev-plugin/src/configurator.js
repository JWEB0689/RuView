import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const pluginRoot = path.resolve(__dirname, '..');
const cliBinPath = path.resolve(pluginRoot, 'bin', 'cli.js');

/**
 * Configure MCP servers in ~/.claude.json for Claude Code.
 */
export function configureClaudeJson(options = {}) {
  const seedUrl = options.seedUrl || 'http://169.254.42.1';
  const homeDir = os.homedir();
  const claudeJsonPath = options.claudeJsonPath || path.join(homeDir, '.claude.json');

  let config = {};
  if (fs.existsSync(claudeJsonPath)) {
    try {
      const raw = fs.readFileSync(claudeJsonPath, 'utf8');
      config = JSON.parse(raw);
    } catch (err) {
      console.warn(`[WARN] Failed to parse existing ${claudeJsonPath}: ${err.message}. Backing up.`);
      fs.copyFileSync(claudeJsonPath, `${claudeJsonPath}.corrupt.${Date.now()}`);
      config = {};
    }
  }

  if (!config.mcpServers || typeof config.mcpServers !== 'object') {
    config.mcpServers = {};
  }

  config.mcpServers['cognitum-seed'] = {
    command: process.execPath,
    args: [cliBinPath, 'mcp', 'serve', '--seed', seedUrl],
    type: 'stdio',
    env: {
      COGNITUM_SEED_URL: seedUrl
    }
  };

  fs.writeFileSync(claudeJsonPath, JSON.stringify(config, null, 2), 'utf8');

  return {
    path: claudeJsonPath,
    serverName: 'cognitum-seed',
    configured: true
  };
}

/**
 * Configure MCP server in ~/.gemini/config/mcp_config.json for Antigravity.
 */
export function configureAntigravityJson(options = {}) {
  const seedUrl = options.seedUrl || 'http://169.254.42.1';
  const homeDir = os.homedir();
  const geminiConfigDir = path.join(homeDir, '.gemini', 'config');
  const mcpConfigPath = path.join(geminiConfigDir, 'mcp_config.json');

  if (!fs.existsSync(geminiConfigDir)) {
    fs.mkdirSync(geminiConfigDir, { recursive: true });
  }

  let config = { mcpServers: {} };
  if (fs.existsSync(mcpConfigPath)) {
    try {
      const raw = fs.readFileSync(mcpConfigPath, 'utf8');
      config = JSON.parse(raw);
    } catch {
      config = { mcpServers: {} };
    }
  }

  if (!config.mcpServers || typeof config.mcpServers !== 'object') {
    config.mcpServers = {};
  }

  config.mcpServers['cognitum-seed'] = {
    command: process.execPath,
    args: [cliBinPath, 'mcp', 'serve', '--seed', seedUrl],
    type: 'stdio',
    env: {
      COGNITUM_SEED_URL: seedUrl
    }
  };

  fs.writeFileSync(mcpConfigPath, JSON.stringify(config, null, 2), 'utf8');

  return {
    path: mcpConfigPath,
    serverName: 'cognitum-seed',
    configured: true
  };
}

/**
 * Register slash commands, skills, and agents into ~/.claude directory.
 */
export function installClaudePluginFiles() {
  const homeDir = os.homedir();
  const claudeDir = path.join(homeDir, '.claude');

  if (!fs.existsSync(claudeDir)) {
    return { installed: false, reason: '~/.claude directory not found' };
  }

  const installed = [];

  // Commands
  const srcCommands = path.join(pluginRoot, 'commands');
  const destCommands = path.join(claudeDir, 'commands');
  if (fs.existsSync(srcCommands)) {
    fs.mkdirSync(destCommands, { recursive: true });
    for (const file of fs.readdirSync(srcCommands)) {
      if (file.endsWith('.md')) {
        fs.copyFileSync(path.join(srcCommands, file), path.join(destCommands, file));
        installed.push(`commands/${file}`);
      }
    }
  }

  // Skills
  const srcSkills = path.join(pluginRoot, 'skills');
  const destSkills = path.join(claudeDir, 'skills');
  if (fs.existsSync(srcSkills)) {
    for (const skillName of fs.readdirSync(srcSkills)) {
      const skillDir = path.join(srcSkills, skillName);
      if (fs.statSync(skillDir).isDirectory()) {
        const destSkillDir = path.join(destSkills, skillName);
        fs.mkdirSync(destSkillDir, { recursive: true });
        for (const file of fs.readdirSync(skillDir)) {
          fs.copyFileSync(path.join(skillDir, file), path.join(destSkillDir, file));
        }
        installed.push(`skills/${skillName}`);
      }
    }
  }

  // Agents
  const srcAgents = path.join(pluginRoot, 'agents');
  const destAgents = path.join(claudeDir, 'agents');
  if (fs.existsSync(srcAgents)) {
    fs.mkdirSync(destAgents, { recursive: true });
    for (const file of fs.readdirSync(srcAgents)) {
      if (file.endsWith('.md')) {
        fs.copyFileSync(path.join(srcAgents, file), path.join(destAgents, file));
        installed.push(`agents/${file}`);
      }
    }
  }

  return { installed: true, items: installed };
}
