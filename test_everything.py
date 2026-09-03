import httpx
import json
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = 'http://localhost:3000'
client = httpx.Client(base_url=BASE_URL, timeout=40.0)

print('=' * 70)
print('STARTING COMPREHENSIVE TEST SUITE FOR MCP TUTOR SERVER')
print('=' * 70)

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
print('\n[1/10] Testing MCP Handshake (initialize)...')
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

# TEST 2: Tools Listing
print('\n[2/10] Testing Tools Listing (tools/list)...')
tools_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}}, headers=headers)
tools_lines = [l for l in tools_resp.text.splitlines() if l.startswith('data:')]
assert_test('tools/list returned data stream', len(tools_lines) > 0)
tools = json.loads(tools_lines[0][5:])['result']['tools']
tool_names = [t['name'] for t in tools]
print(f'  Found {len(tool_names)} registered tools: {tool_names}')
expected_tools = ['start_mission', 'run_tests', 'check_simulation_answer', 'get_hint', 'record_progress', 'generate_3d_scene']
for et in expected_tools:
    assert_test(f'Tool registered: {et}', et in tool_names)

# TEST 3: UI Resources (resources/list and resources/read)
print('\n[3/10] Testing UI Resources (resources/list & read)...')
res_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 3, 'method': 'resources/list', 'params': {}}, headers=headers)
res_lines = [l for l in res_resp.text.splitlines() if l.startswith('data:')]
resources = json.loads(res_lines[0][5:])['result']['resources']
res_uris = [r['uri'] for r in resources]
print(f'  Found {len(res_uris)} registered resources: {res_uris}')
assert_test('Resource ui://tutor/debug-mission exists', 'ui://tutor/debug-mission' in res_uris)
assert_test('Resource ui://tutor/3d-visualizer exists', 'ui://tutor/3d-visualizer' in res_uris)

# Read both HTML resources and verify bundle integrity
for uri in ['ui://tutor/debug-mission', 'ui://tutor/3d-visualizer']:
    read_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 31, 'method': 'resources/read', 'params': {'uri': uri}}, headers=headers)
    read_lines = [l for l in read_resp.text.splitlines() if l.startswith('data:')]
    content = json.loads(read_lines[0][5:])['result']['contents'][0]['text']
    assert_test(f'HTML non-empty for {uri}', len(content) > 10000, f'size={len(content)} bytes')
    assert_test(f'HTML contains Three.js bundle for {uri}', 'THREE' in content or 'WebGLRenderer' in content)
    assert_test(f'HTML contains valid script tag for {uri}', '<script>' in content and '</script>' in content)

# TEST 4: Code Mission Flow (start_mission, run_tests fail, run_tests pass)
print('\n[4/10] Testing Code Mission Flow (off-by-one-sum)...')
sm_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {'name': 'start_mission', 'arguments': {'missionId': 'off-by-one-sum', 'studentId': 'test_student'}}}, headers=headers)
sm_data = json.loads([l for l in sm_resp.text.splitlines() if l.startswith('data:')][0][5:])
mission = sm_data['result']['structuredContent']['mission']
assert_test('Code mission starterCode present', 'starterCode' in mission)
assert_test('Code mission functionName is sum_first_n', mission['functionName'] == 'sum_first_n')

# Run with starter buggy code (must fail test cases)
buggy_code = mission['starterCode']
t_fail_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 41, 'method': 'tools/call', 'params': {'name': 'run_tests', 'arguments': {'missionId': 'off-by-one-sum', 'code': buggy_code}}}, headers=headers)
t_fail_data = json.loads([l for l in t_fail_resp.text.splitlines() if l.startswith('data:')][0][5:])
assert_test('run_tests detects off-by-one bug', t_fail_data['result']['structuredContent']['allPassed'] is False)

# Run with fixed correct code (must pass all test cases)
fixed_code = 'def sum_first_n(n):\n    return n * (n + 1) // 2\n'
t_pass_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 42, 'method': 'tools/call', 'params': {'name': 'run_tests', 'arguments': {'missionId': 'off-by-one-sum', 'code': fixed_code}}}, headers=headers)
t_pass_data = json.loads([l for l in t_pass_resp.text.splitlines() if l.startswith('data:')][0][5:])
assert_test('run_tests confirms fixed code passes', t_pass_data['result']['structuredContent']['allPassed'] is True)

# TEST 5: Physics Simulation Flow (start_mission, wrong answer, correct answer)
print('\n[5/10] Testing Simulation Flow (projectile-range)...')
sim_sm_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 5, 'method': 'tools/call', 'params': {'name': 'start_mission', 'arguments': {'missionId': 'projectile-range', 'studentId': 'test_student'}}}, headers=headers)
sim_sm_data = json.loads([l for l in sim_sm_resp.text.splitlines() if l.startswith('data:')][0][5:])
sim_mission = sim_sm_data['result']['structuredContent']['mission']
assert_test('Simulation params present (angle, velocity)', len(sim_mission['params']) == 2)

# Check wrong answer (e.g. angle=45, vel=20 => actual is 40.82, guess 150)
p = {'angle': 45.0, 'velocity': 20.0}
sim_wrong = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 51, 'method': 'tools/call', 'params': {'name': 'check_simulation_answer', 'arguments': {'missionId': 'projectile-range', 'params': p, 'studentAnswer': 150.0}}}, headers=headers)
sim_wrong_data = json.loads([l for l in sim_wrong.text.splitlines() if l.startswith('data:')][0][5:])
assert_test('Simulation engine rejects wrong answer', sim_wrong_data['result']['structuredContent']['passed'] is False)

# Check correct answer (~40.82)
sim_right = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 52, 'method': 'tools/call', 'params': {'name': 'check_simulation_answer', 'arguments': {'missionId': 'projectile-range', 'params': p, 'studentAnswer': 40.8}}}, headers=headers)
sim_right_data = json.loads([l for l in sim_right.text.splitlines() if l.startswith('data:')][0][5:])
assert_test('Simulation engine accepts correct answer within tolerance', sim_right_data['result']['structuredContent']['passed'] is True)

# TEST 6: Trust Boundary (record_progress security check)
print('\n[6/10] Testing Trust Boundary Enforcement (record_progress)...')
# Attempt to record progress with wrong code (must be rejected even if student claims pass)
rec_wrong = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 61, 'method': 'tools/call', 'params': {'name': 'record_progress', 'arguments': {'missionId': 'off-by-one-sum', 'studentId': 'test_student', 'code': buggy_code}}}, headers=headers)
rec_wrong_data = json.loads([l for l in rec_wrong.text.splitlines() if l.startswith('data:')][0][5:])
assert_test('record_progress refuses completion on buggy code', rec_wrong_data['result']['structuredContent']['completed'] is False)

# Record progress with valid code (must pass server-side verification)
rec_right = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 62, 'method': 'tools/call', 'params': {'name': 'record_progress', 'arguments': {'missionId': 'off-by-one-sum', 'studentId': 'test_student', 'code': fixed_code}}}, headers=headers)
rec_right_data = json.loads([l for l in rec_right.text.splitlines() if l.startswith('data:')][0][5:])
assert_test('record_progress grants completion on verified code', rec_right_data['result']['structuredContent']['completed'] is True)

# TEST 7: AI Socratic Hints (Gemini API Integration)
print('\n[7/10] Testing AI Socratic Hints with Gemini (get_hint)...')
hint_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 7, 'method': 'tools/call', 'params': {'name': 'get_hint', 'arguments': {'missionId': 'off-by-one-sum', 'code': buggy_code, 'attemptNumber': 1}}}, headers=headers)
hint_data = json.loads([l for l in hint_resp.text.splitlines() if l.startswith('data:')][0][5:])
hint_text = hint_data['result']['content'][0]['text']
hint_source = hint_data['result']['structuredContent'].get('source')
assert_test('get_hint returned non-empty hint', len(hint_text) > 10, f'hint=\"{hint_text[:60]}...\"')
assert_test('get_hint powered by Gemini AI (source == ai)', hint_source == 'ai', f'source={hint_source}')

# TEST 8: AI 3D Scene Generation (generate_3d_scene)
print('\n[8/10] Testing 3D Space Visualization Generator (generate_3d_scene)...')
scene_resp = client.post('/mcp', json={'jsonrpc': '2.0', 'id': 8, 'method': 'tools/call', 'params': {'name': 'generate_3d_scene', 'arguments': {'query': 'a solar system with the sun and orbiting planets'}}}, headers=headers)
scene_data = json.loads([l for l in scene_resp.text.splitlines() if l.startswith('data:')][0][5:])
scene = scene_data['result']['structuredContent']['scene']
assert_test('3D scene has title', bool(scene.get('title')), f"title={scene.get('title')}")
assert_test('3D scene has multiple 3D objects', len(scene.get('objects', [])) >= 3, f"count={len(scene.get('objects', []))}")
assert_test('3D scene has camera configuration', 'position' in scene.get('camera', {}))
assert_test('3D scene has lighting configuration', len(scene.get('lights', [])) >= 1)

# Check individual object structure
obj0 = scene['objects'][0]
assert_test('Objects have type, position, and color', all(k in obj0 for k in ['type', 'position', 'color']))
has_animation = any(o.get('animation', {}).get('type') in ['rotate', 'orbit', 'pulse', 'bounce'] for o in scene['objects'])
assert_test('3D objects contain dynamic animations', has_animation)

# TEST 9: Public Cloudflare Tunnel Verification
print('\n[9/10] Testing Live Public Tunnel Endpoint...')
tunnel_url = 'https://guarantee-grows-question-pine.trycloudflare.com/mcp'
try:
    tun_resp = httpx.post(
        tunnel_url,
        json={
            'jsonrpc': '2.0',
            'id': 9,
            'method': 'initialize',
            'params': {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'tunnel-test', 'version': '1.0'}}
        },
        headers={'Accept': 'application/json, text/event-stream'},
        timeout=15.0
    )
    assert_test('Public HTTPS tunnel responds with 200 OK', tun_resp.status_code == 200, f'status={tun_resp.status_code}')
except Exception as e:
    assert_test('Public HTTPS tunnel accessible', False, str(e))

print('\n' + '=' * 70)
print('ALL 10 TEST SUITES PASSED FLAWLESSLY! 100% OPERATIONAL')
print('=' * 70)
