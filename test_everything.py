import httpx
import json
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = 'http://localhost:3000'
client = httpx.Client(base_url=BASE_URL, timeout=40.0)

print('=' * 75)
print('STARTING COMPREHENSIVE 15-POINT TEST SUITE FOR ALL 13 TOOLS & 6 UI WIDGETS')
print('=' * 75)

report = {}

def assert_test(name, condition, details=''):
    if condition:
        print(f'  [PASS] {name}')
        report[name] = ('PASS', details)
    else:
        print(f'  [FAIL] {name}: {details}')
        report[name] = ('FAIL', details)
        sys.exit(1)

# TEST 1: MCP Handshake
print('\n[1/15] Testing MCP Handshake (initialize)...')
init_resp = client.post(
    '/mcp',
    json={
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'initialize',
        'params': {
            'protocolVersion': '2025-06-18',
            'capabilities': {},
            'clientInfo': {'name': 'comprehensive-suite', 'version': '1.0'}
        }
    },
    headers={'Accept': 'application/json, text/event-stream'}
)
sid = init_resp.headers.get('mcp-session-id')
assert_test('Initialize handshake returns 200', init_resp.status_code == 200, f'status={init_resp.status_code}')
assert_test('Session ID header generated', bool(sid), f'sid={sid}')

headers = {'Accept': 'application/json, text/event-stream', 'Mcp-Session-Id': sid}

# TEST 2: Tools Listing (All 13 Tools)
print('\n[2/15] Testing Tools Listing (tools/list)...')
tools_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}}, headers=headers)
tools_lines = [l for l in tools_resp.text.splitlines() if l.startswith('data:')]
assert_test('tools/list returned data stream', len(tools_lines) > 0)
tools = json.loads(tools_lines[0][5:])['result']['tools']
tool_names = [t['name'] for t in tools]
print(f'  Found {len(tool_names)} registered tools: {tool_names}')
expected_tools = [
    'start_mission', 'run_tests', 'check_simulation_answer', 'get_hint',
    'record_progress', 'generate_3d_scene', 'visualize_math_surface',
    'preview_html_css', 'run_code_scratchpad', 'get_student_analytics',
    'visualize_algorithm_3d', 'interactive_audio_synth', 'physics_rigid_body_playground'
]
assert_test('Exactly 13 tools registered', len(tool_names) == 13, f'got {len(tool_names)}')
for et in expected_tools:
    assert_test(f'Tool registered: {et}', et in tool_names)

# TEST 3: UI Resources (All 6 HTML Widgets)
print('\n[3/15] Testing UI Resources (resources/list & read)...')
res_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 3, 'method': 'resources/list', 'params': {}}, headers=headers)
res_lines = [l for l in res_resp.text.splitlines() if l.startswith('data:')]
resources = json.loads(res_lines[0][5:])['result']['resources']
res_uris = [r['uri'] for r in resources]
print(f'  Found {len(res_uris)} registered resources: {res_uris}')
expected_uris = [
    'ui://tutor/debug-mission',
    'ui://tutor/3d-visualizer',
    'ui://tutor/web-sandbox',
    'ui://tutor/algo-visualizer',
    'ui://tutor/audio-synth',
    'ui://tutor/physics-playground',
]
assert_test('Exactly 6 UI resources registered', len(res_uris) == 6, f'got {len(res_uris)}')
for eu in expected_uris:
    assert_test(f'Resource {eu} exists', eu in res_uris)

for uri in res_uris:
    read_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 31, 'method': 'resources/read', 'params': {'uri': uri}}, headers=headers)
    read_lines = [l for l in read_resp.text.splitlines() if l.startswith('data:')]
    content = json.loads(read_lines[0][5:])['result']['contents'][0]['text']
    assert_test(f'HTML non-empty for {uri}', len(content) > 1000, f'size={len(content)} bytes')
    assert_test(f'HTML contains script for {uri}', '<script>' in content and '</script>' in content)

# TEST 4: Code Mission Flow (off-by-one-sum)
print('\n[4/15] Testing Code Mission Flow (off-by-one-sum)...')
sm_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {'name': 'start_mission', 'arguments': {'missionId': 'off-by-one-sum', 'studentId': 'test_student'}}}, headers=headers)
sm_data = json.loads([l for l in sm_resp.text.splitlines() if l.startswith('data:')][0][5:])
mission = sm_data['result']['structuredContent']['mission']
buggy_code = mission['starterCode']
t_fail_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 41, 'method': 'tools/call', 'params': {'name': 'run_tests', 'arguments': {'missionId': 'off-by-one-sum', 'code': buggy_code}}}, headers=headers)
t_fail_data = json.loads([l for l in t_fail_resp.text.splitlines() if l.startswith('data:')][0][5:])
assert_test('run_tests detects bug', t_fail_data['result']['structuredContent']['allPassed'] is False)

fixed_code = 'def sum_first_n(n):\n    return n * (n + 1) // 2\n'
t_pass_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 42, 'method': 'tools/call', 'params': {'name': 'run_tests', 'arguments': {'missionId': 'off-by-one-sum', 'code': fixed_code}}}, headers=headers)
t_pass_data = json.loads([l for l in t_pass_resp.text.splitlines() if l.startswith('data:')][0][5:])
assert_test('run_tests confirms fixed code passes', t_pass_data['result']['structuredContent']['allPassed'] is True)

# TEST 5: Physics Simulation Flow (projectile-range)
print('\n[5/15] Testing Simulation Flow (projectile-range)...')
p = {'angle': 45.0, 'velocity': 20.0}
sim_wrong = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 51, 'method': 'tools/call', 'params': {'name': 'check_simulation_answer', 'arguments': {'missionId': 'projectile-range', 'params': p, 'studentAnswer': 150.0}}}, headers=headers)
sim_wrong_data = json.loads([l for l in sim_wrong.text.splitlines() if l.startswith('data:')][0][5:])
assert_test('Simulation rejects wrong answer', sim_wrong_data['result']['structuredContent']['passed'] is False)

sim_right = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 52, 'method': 'tools/call', 'params': {'name': 'check_simulation_answer', 'arguments': {'missionId': 'projectile-range', 'params': p, 'studentAnswer': 40.8}}}, headers=headers)
sim_right_data = json.loads([l for l in sim_right.text.splitlines() if l.startswith('data:')][0][5:])
assert_test('Simulation accepts correct answer', sim_right_data['result']['structuredContent']['passed'] is True)

# TEST 6: Trust Boundary Enforcement (record_progress)
print('\n[6/15] Testing Trust Boundary Enforcement (record_progress)...')
fresh_student = f'student_{int(time.time())}'
rec_wrong = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 61, 'method': 'tools/call', 'params': {'name': 'record_progress', 'arguments': {'missionId': 'off-by-one-sum', 'studentId': fresh_student, 'code': buggy_code}}}, headers=headers)
rec_wrong_data = json.loads([l for l in rec_wrong.text.splitlines() if l.startswith('data:')][0][5:])
assert_test('record_progress refuses completion on buggy code', rec_wrong_data['result']['structuredContent']['completed'] is False)

rec_right = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 62, 'method': 'tools/call', 'params': {'name': 'record_progress', 'arguments': {'missionId': 'off-by-one-sum', 'studentId': fresh_student, 'code': fixed_code}}}, headers=headers)
rec_right_data = json.loads([l for l in rec_right.text.splitlines() if l.startswith('data:')][0][5:])
assert_test('record_progress grants completion on verified code', rec_right_data['result']['structuredContent']['completed'] is True)

# TEST 7: AI Socratic Hints with Gemini (get_hint)
print('\n[7/15] Testing AI Socratic Hints with Gemini (get_hint)...')
hint_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 7, 'method': 'tools/call', 'params': {'name': 'get_hint', 'arguments': {'missionId': 'off-by-one-sum', 'code': buggy_code, 'attemptNumber': 1}}}, headers=headers)
hint_data = json.loads([l for l in hint_resp.text.splitlines() if l.startswith('data:')][0][5:])
hint_text = hint_data['result']['content'][0]['text']
hint_source = hint_data['result']['structuredContent'].get('source')
assert_test('get_hint returned non-empty hint', len(hint_text) > 10)
assert_test('get_hint powered by Gemini AI (source == ai)', hint_source == 'ai')

# TEST 8: AI 3D Space Scene Generation (generate_3d_scene)
print('\n[8/15] Testing 3D Space Visualization Generator (generate_3d_scene)...')
scene_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 8, 'method': 'tools/call', 'params': {'name': 'generate_3d_scene', 'arguments': {'query': 'a solar system with the sun and orbiting planets'}}}, headers=headers)
scene_data = json.loads([l for l in scene_resp.text.splitlines() if l.startswith('data:')][0][5:])
scene = scene_data['result']['structuredContent']['scene']
assert_test('3D scene has title', bool(scene.get('title')))
assert_test('3D scene has objects', len(scene.get('objects', [])) >= 3)
assert_test('3D scene has camera & lighting', 'position' in scene.get('camera', {}) and len(scene.get('lights', [])) >= 1)

# TEST 9: 3D Mathematical Surface Plotter (visualize_math_surface)
print('\n[9/15] Testing 3D Mathematical Surface Plotter (visualize_math_surface)...')
math_resp = client.post(
    '/mcp',
    json={
        'jsonrpc': '2.0',
        'id': 9,
        'method': 'tools/call',
        'params': {
            'name': 'visualize_math_surface',
            'arguments': {
                'expression': 'sin(sqrt(x**2 + y**2))',
                'xRange': [-4.0, 4.0],
                'yRange': [-4.0, 4.0],
                'resolution': 20,
                'color': '#00ffcc'
            }
        }
    },
    headers=headers
)
math_data = json.loads([l for l in math_resp.text.splitlines() if l.startswith('data:')][0][5:])
math_scene = math_data['result']['structuredContent']['scene']
assert_test('Math surface title generated', 'sin(sqrt(x**2 + y**2))' in math_scene.get('title', ''))
surface_obj = math_scene['objects'][0]
assert_test('Math surface type is surface', surface_obj['type'] == 'surface')
assert_test('Math surface heights array generated', len(surface_obj['surfaceGrid']['heights']) == (20 + 1) * (20 + 1))

# TEST 10: Interactive Web Sandbox Preview (preview_html_css)
print('\n[10/15] Testing Interactive Web Sandbox (preview_html_css)...')
sandbox_resp = client.post(
    '/mcp',
    json={
        'jsonrpc': '2.0',
        'id': 10,
        'method': 'tools/call',
        'params': {
            'name': 'preview_html_css',
            'arguments': {
                'title': 'Neon Gradient Card',
                'html': '<div class=\"card\"><h3>Interactive Card</h3></div>',
                'css': '.card { padding: 20px; color: white; }',
            }
        }
    },
    headers=headers
)
sandbox_data = json.loads([l for l in sandbox_resp.text.splitlines() if l.startswith('data:')][0][5:])
sandbox_payload = sandbox_data['result']['structuredContent']['sandbox']
assert_test('Sandbox title matches', sandbox_payload['title'] == 'Neon Gradient Card')
assert_test('Sandbox HTML retained', 'Interactive Card' in sandbox_payload['html'])

# TEST 11: Python Scratchpad & Learning Analytics
print('\n[11/15] Testing Python Scratchpad & Learning Analytics...')
scratch_resp = client.post(
    '/mcp',
    json={
        'jsonrpc': '2.0',
        'id': 111,
        'method': 'tools/call',
        'params': {'name': 'run_code_scratchpad', 'arguments': {'code': 'print(\"SUM:\", sum(range(10)))'}}
    },
    headers=headers
)
scratch_data = json.loads([l for l in scratch_resp.text.splitlines() if l.startswith('data:')][0][5:])
assert_test('Scratchpad output correct', 'SUM: 45' in scratch_data['result']['structuredContent']['stdout'])

analytics_resp = client.post(
    '/mcp',
    json={
        'jsonrpc': '2.0',
        'id': 112,
        'method': 'tools/call',
        'params': {'name': 'get_student_analytics', 'arguments': {'studentId': fresh_student}}
    },
    headers=headers
)
analytics_data = json.loads([l for l in analytics_resp.text.splitlines() if l.startswith('data:')][0][5:])
assert_test('Analytics tracked student', analytics_data['result']['structuredContent']['studentId'] == fresh_student)

# TEST 12: NEW SYSTEM 1 - 3D Algorithm Step-by-Step Visualizer
print('\n[12/15] Testing 3D Algorithm Visualizer (visualize_algorithm_3d)...')
algo_resp = client.post(
    '/mcp',
    json={
        'jsonrpc': '2.0',
        'id': 12,
        'method': 'tools/call',
        'params': {'name': 'visualize_algorithm_3d', 'arguments': {'algorithm': 'bubble_sort', 'data': [24, 12, 35, 8, 19]}}
    },
    headers=headers
)
algo_data = json.loads([l for l in algo_resp.text.splitlines() if l.startswith('data:')][0][5:])
algo_trace = algo_data['result']['structuredContent']['algorithmTrace']
assert_test('Algorithm title matches', 'Bubble Sort' in algo_trace['algorithm'])
assert_test('Algorithm computed step sequence', algo_trace['totalSteps'] >= 5)
assert_test('Algorithm step contains comparisons and swaps', 'comparisons' in algo_trace['steps'][-1])

# TEST 13: NEW SYSTEM 2 - Interactive Web Audio Synthesizer
print('\n[13/15] Testing Web Audio Synthesizer (interactive_audio_synth)...')
audio_resp = client.post(
    '/mcp',
    json={
        'jsonrpc': '2.0',
        'id': 13,
        'method': 'tools/call',
        'params': {'name': 'interactive_audio_synth', 'arguments': {'preset': 'cyberpunk_lead', 'waveform': 'sawtooth'}}
    },
    headers=headers
)
audio_data = json.loads([l for l in audio_resp.text.splitlines() if l.startswith('data:')][0][5:])
synth_cfg = audio_data['result']['structuredContent']['synthConfig']
assert_test('Synthesizer waveform is sawtooth', synth_cfg['waveform'] == 'sawtooth')
assert_test('Synthesizer has baseFrequency', synth_cfg['baseFrequency'] == 220.0)
assert_test('Synthesizer wave equation provided', bool(synth_cfg['equation']))

# TEST 14: NEW SYSTEM 3 - Rigid-Body Physics Playground (Cannon-es)
print('\n[14/15] Testing 3D Rigid-Body Physics Playground (physics_rigid_body_playground)...')
physics_resp = client.post(
    '/mcp',
    json={
        'jsonrpc': '2.0',
        'id': 14,
        'method': 'tools/call',
        'params': {'name': 'physics_rigid_body_playground', 'arguments': {'sceneType': 'domino_chain', 'gravityPreset': 'earth'}}
    },
    headers=headers
)
physics_data = json.loads([l for l in physics_resp.text.splitlines() if l.startswith('data:')][0][5:])
physics_world = physics_data['result']['structuredContent']['physicsWorld']
assert_test('Physics gravity is Earth (-9.82 m/s²)', physics_world['gravity'] == -9.82)
assert_test('Physics domino chain has rigid bodies', len(physics_world['objects']) >= 10)
assert_test('Physics restitution set', 'restitution' in physics_world)

# TEST 15: Public Cloudflare Tunnel Verification
print('\n[15/15] Testing Live Public Tunnel Endpoint...')
tunnel_url = 'https://guarantee-grows-question-pine.trycloudflare.com/mcp'
try:
    tun_resp = httpx.post(
        tunnel_url,
        json={
            'jsonrpc': '2.0',
            'id': 15,
            'method': 'initialize',
            'params': {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'tunnel-test', 'version': '1.0'}}
        },
        headers={'Accept': 'application/json, text/event-stream'},
        timeout=15.0
    )
    assert_test('Public HTTPS tunnel responds with 200 OK', tun_resp.status_code == 200, f'status={tun_resp.status_code}')
except Exception as e:
    assert_test('Public HTTPS tunnel accessible', False, str(e))

print('\n' + '=' * 75)
print('ALL 15 TEST SUITES PASSED! ALL 13 TOOLS & 6 WIDGETS ARE 100% OPERATIONAL!')
print('=' * 75)
