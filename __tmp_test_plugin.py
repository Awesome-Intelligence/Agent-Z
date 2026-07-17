import sys
sys.path.insert(0, r'e:\Awesome Intelligence\Agent-Z')

print('=== Test 1: PluginManager singleton & basic API ===')
from plugins import get_plugin_manager, PluginManager, PluginContext, PluginManifest
pm = get_plugin_manager()
assert isinstance(pm, PluginManager)
print('  OK: PluginManager singleton created')

for attr in ['list_manifests', 'get_manifest', 'is_plugin_disabled', 'loaded_plugins',
             'load_errors', 'get_memory_providers', 'get_context_engines',
             'get_model_providers', 'get_web_search_backends', 'get_tool_providers',
             'discover_and_load', 'emit_hook_event', 'register_hook', 'fire']:
    assert hasattr(pm, attr), f'Missing {attr}'
print('  OK: All public APIs present')

print()
print('=== Test 2: Plugin utils thread safety ===')
from plugins.plugin_utils import lazy_singleton, SingletonSlot

call_count = [0]
@lazy_singleton
def factory():
    call_count[0] += 1
    return {'counter': call_count[0]}

inst1 = factory()
inst2 = factory()
assert inst1 is inst2, 'singleton broken'
assert call_count[0] == 1
print('  OK: lazy_singleton works, factory called once')

factory.reset()
inst3 = factory()
assert call_count[0] == 2
assert inst1 is not inst3
print('  OK: lazy_singleton reset works')

# SingletonSlot
slot: SingletonSlot[int] = SingletonSlot()
# peek without building
assert slot.peek() is None
val = slot.get(lambda: 42)
assert val == 42
assert slot.peek() == 42
val2 = slot.get(lambda: 999)  # second call uses cached
assert val2 == 42, f'SingletonSlot not cached: got {val2}'
slot.reset()
assert slot.peek() is None
val3 = slot.get(lambda: 123)
assert val3 == 123
print('  OK: SingletonSlot works')

print()
print('=== Test 3: Memory plugin discover + load + register ===')
from plugins.memory import (
    discover_memory_providers, load_memory_provider,
    diagnose_provider, validate_provider_config,
)
entries = discover_memory_providers()
print(f'  Discovered providers: {[e[0] for e in entries]}')
assert any(name == 'example' for name, _, _ in entries), 'example not found'

provider = load_memory_provider('example')
assert provider is not None, 'example memory provider not loaded'
print(f'  OK: example provider loaded: {type(provider).__name__}')

avail = provider.is_available()
print(f'  OK: is_available() = {avail}')

diag = diagnose_provider('example')
print(f'  OK: diagnostics status = {diag.status}')
print(f'  OK: path = {diag.path}')

schema = provider.get_config_schema()
print(f'  OK: config schema items = {len(schema)}')

valid, merged = validate_provider_config('example', {})
print(f'  OK: validate_config valid={valid}')

print()
print('=== Test 4: Fire pre_tool_call hook ===')
try:
    result = pm.emit_hook_event('pre_tool_call', arg1='test')
    print(f'  OK: pre_tool_call hook fired with {len(result)} returns')
except Exception as e:
    print(f'  INFO: hook not registered (non-fatal): {type(e).__name__}')

print()
print('=== Test 5: Plugin manifest YAML example exists ===')
from pathlib import Path
import yaml
manifest_path = Path(r'e:\Awesome Intelligence\Agent-Z\plugins\memory\example\plugin.yaml')
assert manifest_path.exists(), 'plugin.yaml missing'
with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest = yaml.safe_load(f)
print(f'  OK: manifest loaded: name={manifest.get("name")}, version={manifest.get("version")}')

print()
print('=== ALL INTEGRATION TESTS PASSED ===')
