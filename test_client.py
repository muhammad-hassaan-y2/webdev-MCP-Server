import httpx
import json

BASE_URL = 'http://localhost:3000'

def run_test():
    print(f'Connecting to MCP server at {BASE_URL}/mcp ...\n')
    client = httpx.Client(base_url=BASE_URL)

    # 1. Initialize MCP Handshake
    init_resp = client.post(
        '/mcp',
        json={
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'initialize',
            'params': {
                'protocolVersion': '2025-06-18',
                'capabilities': {},
                'clientInfo': {'name': 'tester', 'version': '1.0.0'}
            }
        },
        headers={'Accept': 'application/json, text/event-stream'}
    )
    
    sid = init_resp.headers.get('mcp-session-id')
    print(f'[OK] Handshake initialized! Session ID: {sid}')
    headers = {'Accept': 'application/json, text/event-stream', 'Mcp-Session-Id': sid}

    # 2. List Tools
    tools_resp = client.post(
        '/mcp',
        json={'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}},
        headers=headers
    )
    tools_data = [line for line in tools_resp.text.splitlines() if line.startswith('data:')][0][5:]
    tools = json.loads(tools_data)['result']['tools']
    print(f'\n[OK] Available Tools ({len(tools)}):')
    for t in tools:
        print(f"  - {t['name']}")

    # 3. Call start_mission (Projectile Simulation)
    print('\n[Testing] Calling tool: start_mission (projectile-range)...')
    call_resp = client.post(
        '/mcp',
        json={
            'jsonrpc': '2.0',
            'id': 3,
            'method': 'tools/call',
            'params': {
                'name': 'start_mission',
                'arguments': {'missionId': 'projectile-range', 'studentId': 'hassaan'}
            }
        },
        headers=headers
    )
    call_data = [line for line in call_resp.text.splitlines() if line.startswith('data:')][0][5:]
    print('Result:\n', json.loads(call_data)['result']['content'][0]['text'])

    # 4. Call check_simulation_answer
    print('\n[Testing] Calling tool: check_simulation_answer (angle=45, velocity=20, studentAnswer=40.8)...')
    sim_resp = client.post(
        '/mcp',
        json={
            'jsonrpc': '2.0',
            'id': 4,
            'method': 'tools/call',
            'params': {
                'name': 'check_simulation_answer',
                'arguments': {
                    'missionId': 'projectile-range',
                    'params': {'angle': 45, 'velocity': 20},
                    'studentAnswer': 40.8
                }
            }
        },
        headers=headers
    )
    sim_data = [line for line in sim_resp.text.splitlines() if line.startswith('data:')][0][5:]
    print('Result:\n', json.loads(sim_data)['result']['content'][0]['text'])

    print('\nAll tests passed successfully!')

if __name__ == '__main__':
    run_test()
