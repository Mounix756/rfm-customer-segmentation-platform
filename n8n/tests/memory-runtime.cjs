// À exécuter dans l'image n8n : test du vrai nœud, avec PostgreSQL de test, sans modèle ni clé API.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const workflow = JSON.parse(fs.readFileSync('/workflow/taiss-tp-final.json', 'utf8'));
const config = workflow.nodes.find(n => n.name === 'Memoire session');
const { MemoryPostgresChat } = require('/usr/local/lib/node_modules/n8n/node_modules/@n8n/n8n-nodes-langchain/dist/nodes/memory/MemoryPostgresChat/MemoryPostgresChat.node.js');
async function memory(sessionId, workflowId = 'runtime-test') {
  const context = {
    getNodeParameter: (name, index, fallback) => name === 'sessionKey' ? `${workflowId}:rfm-chat:${sessionId}` : (config.parameters[name] ?? fallback),
    getCredentials: async () => ({ host: 'postgres', database: 'rfm_memory', user: 'rfm_memory', password: process.env.PGPASSWORD, port: 5432, ssl: 'disable', allowUnauthorizedCerts: false }),
    getWorkflow: () => ({ id: workflowId }),
    getNode: () => config,
    getExecutionId: () => 'runtime-execution',
    getMode: () => 'manual',
    addInputData: () => ({ index: 0 }),
    addOutputData: () => {},
    logAiEvent: () => {},
    logger: { debug() {}, warn() {}, error() {} },
  };
  return (await new MemoryPostgresChat().supplyData.call(context, 0)).response;
}
(async () => {
  if (process.argv[2] === 'verify') {
    const restored = await memory('session-A');
    const history = await restored.loadMemoryVariables({});
    assert.equal(history.chat_history.length, 20);
    assert.equal(history.chat_history[0].content, 'question-2');
    assert.equal(history.chat_history.at(-1).content, 'reponse-11');
    assert.equal((await (await memory('session-B')).loadMemoryVariables({})).chat_history.length, 0);
    console.log('OK : historique conservé après redémarrage PostgreSQL et nouveau processus n8n.');
    process.exit(0);
  }
  const a = await memory('session-A');
  await a.saveContext({ input: 'Parlons des Champions.' }, { output: 'Contexte Champions.' });
  const resumed = await memory('session-A');
  let history = await resumed.loadMemoryVariables({});
  assert.equal(history.chat_history.length, 2);
  assert.equal(history.chat_history[0].content, 'Parlons des Champions.');
  const b = await memory('session-B');
  assert.equal((await b.loadMemoryVariables({})).chat_history.length, 0);
  const otherWorkflow = await memory('session-A', 'other-workflow');
  assert.equal((await otherWorkflow.loadMemoryVariables({})).chat_history.length, 0);
  for (let i = 0; i < 12; i++) await resumed.saveContext({ input: `question-${i}` }, { output: `reponse-${i}` });
  history = await resumed.loadMemoryVariables({});
  assert.equal(history.chat_history.length, 20);
  assert.equal(history.chat_history[0].content, 'question-2');
  assert.equal(history.chat_history.at(-1).content, 'reponse-11');
  assert.equal((await b.loadMemoryVariables({})).chat_history.length, 0);
  console.log('OK : reprise de session, isolation entre sessions/workflows et fenêtre de dix interactions.');
  process.exit(0);
})().catch(error => { console.error(error); process.exit(1); });
