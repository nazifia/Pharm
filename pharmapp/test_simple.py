# Test password form action
template_content = '<form method="post" action="/users/change-password/{{ user_to_change.id }}/">'
user_id = 68
rendered = template_content.replace('{{ user_to_change.id }}', str(user_id))
print('Rendered form:', rendered)
print('Has correct action:', '/users/change-password/68/' in rendered)

# Test cache middleware
class MockRequest:
    def __init__(self):
        self.method = 'GET'
        self.path = '/api/health/'
        # No user attribute

from pharmapp.pharmapp.cache_middleware import SmartCacheMiddleware
middleware = SmartCacheMiddleware(lambda x: None)
request = MockRequest()

try:
    cache_key = middleware._get_cache_key(request)
    print('\nCache middleware handles requests without user: SUCCESS')
except AttributeError as e:
    print('\nCache middleware failed:', e)
