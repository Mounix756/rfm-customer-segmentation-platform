// Vérifie les paramètres du vrai nœud installé sans appel fournisseur.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const config = JSON.parse(fs.readFileSync('/workflow/taiss-tp-final.json', 'utf8')).nodes.find(n => n.name === 'Modele DeepSeek');
const { LmChatOpenAi } = require('/usr/local/lib/node_modules/n8n/node_modules/@n8n/n8n-nodes-langchain/dist/nodes/llms/LMChatOpenAi/LmChatOpenAi.node.js');
const context = {
  getNodeParameter: (name, index, fallback) => name === 'model.value' ? config.parameters.model.value : (config.parameters[name] ?? fallback),
  getCredentials: async () => ({ apiKey: 'test-only-not-a-key', url: 'https://api.deepseek.com' }),
  getWorkflow: () => ({ id: 'model-test' }), getNode: () => config,
  getExecutionId: () => 'test', getMode: () => 'manual',
  addInputData: () => ({ index: 0 }), addOutputData: () => {}, logAiEvent: () => {},
  logger: { debug() {}, warn() {}, error() {} },
};
(async () => {
  const { response } = await new LmChatOpenAi().supplyData.call(context, 0);
  assert.equal(response.model, 'deepseek-v4-flash');
  assert.deepEqual(response.modelKwargs.thinking, { type: 'disabled' });
  assert.equal(response.clientConfig.baseURL, 'https://api.deepseek.com');
  console.log('OK : modèle DeepSeek, URL et thinking désactivé dans le vrai nœud.');
})().catch(e => { console.error(e); process.exit(1); });
