import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const workflow = JSON.parse(fs.readFileSync(new URL('../taiss-tp-final.json', import.meta.url), 'utf8'));
const nodes = Object.fromEntries(workflow.nodes.map(node => [node.name, node]));
const run = (name, json) => new Function('$input', '$', nodes[name].parameters.jsCode)({ first: () => ({ json }) }, () => ({ first: () => ({ json: { sessionId: 'session-test-001' } }) }))[0].json;

test('export public inactif, sans identifiants de compte ni données épinglées', () => {
  assert.equal(workflow.active, false);
  assert.equal(workflow.id, 'rfmMarketingTemplate');
  for (const key of ['versionId', 'meta']) assert.equal(key in workflow, false);
  assert.deepEqual(workflow.pinData, {});
  for (const node of workflow.nodes) {
    assert.equal('credentials' in node, false);
    assert.equal('sendHeaders' in node.parameters, false);
  }
  assert.equal(nodes.Webhook.parameters.authentication, 'headerAuth');
});

test('toutes les connexions ciblent des nœuds existants', () => {
  assert.equal(new Set(workflow.nodes.map(n => n.id)).size, workflow.nodes.length);
  for (const [source, connections] of Object.entries(workflow.connections)) {
    assert.ok(nodes[source]);
    for (const branches of Object.values(connections)) {
      for (const branch of branches) for (const edge of branch) assert.ok(nodes[edge.node]);
    }
  }
  assert.equal(workflow.connections['Message valide'].main[0][0].node, 'Agent Marketing');
  assert.equal(workflow.connections['Message valide'].main[1][0].node, 'Repondre');
  assert.equal(workflow.connections['Agent Marketing'].main[1][0].node, 'Erreur assistant');
});

test('rejeter corps absent, tableau, objet et message invalide avant le modèle', () => {
  for (const body of [undefined, null, [], 'bonjour', {}, { message: 42 }, { message: {} }, { message: '  ' }, { message: 'x'.repeat(2001) }]) {
    const result = run('Configuration', { body: body && typeof body === 'object' && !Array.isArray(body) ? { ...body, sessionId: 'session-test-001' } : body });
    assert.equal(result.valid, false);
    assert.equal(result.statusCode, 400);
    assert.equal(result.body.ok, false);
  }
});

test('préserver un texte valide et interdire la modification de l’URL par la requête', () => {
  const result = run('Configuration', { body: { sessionId: 'session-test-001', message: '  À risque ?  ', apiBaseUrl: 'https://example.invalid' } });
  assert.equal(result.valid, true);
  assert.equal(result.message, 'À risque ?');
  assert.equal(result.apiBaseUrl, 'http://segmentation-api:8000');
  assert.equal(run('Configuration', { body: { sessionId: 'session-test-001', message: 'x'.repeat(2000) } }).valid, true);
});

test('outils agrégés et encodage du nom de segment', () => {
  const tools = workflow.nodes.filter(n => n.type === 'n8n-nodes-base.httpRequestTool');
  assert.equal(tools.length, 7);
  const lookup = () => ({ first: () => ({ json: { apiBaseUrl: 'http://segmentation-api:8000' } }) });
  for (const tool of tools) {
    assert.equal(tool.parameters.method, 'GET');
    const url = new Function('$', '$fromAI', 'return ' + tool.parameters.url.slice(3, -2))(lookup, () => 'À risque/../?');
    assert.equal(url.startsWith('http://segmentation-api:8000/'), true);
    assert.equal(url.includes('/rfm-clients-segments'), false);
    if (tool.name === 'FicheSegment') assert.equal(url, 'http://segmentation-api:8000/segments/' + encodeURIComponent('À risque/../?'));
  }
});

test('contrat JSON de réponse et erreurs sans détails internes', () => {
  assert.deepEqual(run('Preparer reponse', { output: ' Réponse vérifiée ' }), { statusCode: 200, body: { ok: true, sessionId: 'session-test-001', answer: 'Réponse vérifiée' } });
  for (const output of [null, '', {}, '  ']) assert.equal(run('Preparer reponse', { output }).statusCode, 502);
  const error = run('Erreur assistant', { error: 'sensitive-internal-detail' });
  assert.equal(error.statusCode, 502);
  assert.equal(JSON.stringify(error).includes('sensitive-internal-detail'), false);
  assert.equal(nodes.Repondre.parameters.respondWith, 'json');
});


test('session obligatoire, format strict et aucune session de secours commune', () => {
  for (const sessionId of [undefined, null, 42, {}, [], '', 'short', '  session-001', 'session-001 ', 'session/001', 'session:001', 'session-é001', 'x'.repeat(129)]) {
    const result = run('Configuration', { body: { sessionId, message: 'Bonjour' } });
    assert.equal(result.valid, false);
    assert.equal(result.statusCode, 400);
    assert.match(result.body.error, /sessionId/);
  }
  for (const sessionId of ['sessionA', 'SessionA', 'x'.repeat(128), '608fce37-35bd-4b64-9236-88c5c02fb478']) {
    const result = run('Configuration', { body: { sessionId, message: 'Bonjour' } });
    assert.equal(result.valid, true);
    assert.equal(result.sessionId, sessionId);
  }
});

test('mémoire branchée et clés distinctes selon sessionId', () => {
  const memory = nodes['Memoire session'];
  assert.equal(memory.type, '@n8n/n8n-nodes-langchain.memoryPostgresChat');
  assert.equal(memory.parameters.sessionIdType, 'customKey');
  assert.equal(memory.parameters.contextWindowLength, 10);
  assert.equal(workflow.connections['Memoire session'].ai_memory[0][0].node, 'Agent Marketing');
  const key = (sessionId, workflowId = 'workflow-A') => new Function('$', '$workflow', 'return ' + memory.parameters.sessionKey.slice(3, -2))(() => ({ first: () => ({ json: { sessionId } }) }), { id: workflowId });
  assert.equal(key('sessionA'), key('sessionA'));
  assert.notEqual(key('sessionA'), key('sessionB'));
  assert.notEqual(key('sessionA'), key('SessionA'));
  assert.equal(key('sessionA'), 'workflow-A:rfm-chat:sessionA');
  assert.notEqual(key('sessionA', 'workflow-A'), key('sessionA', 'workflow-B'));
  assert.equal(memory.parameters.tableName, 'rfm_chat_histories');
});
