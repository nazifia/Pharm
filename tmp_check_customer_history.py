from django.test import Client
c=Client()
if not c.login(mobile='99900011122', password='Password123'):
    print('login failed')
else:
    r=c.get('/customer_history/4/')
    html=r.content.decode('utf-8')
    import re
    body_count = html.count('<div class="container">')
    print('status', r.status_code)
    print('container count', body_count)
    print('has extra closing </div> after container:', re.search(r'</div>\s*</div>\s*<', html) is not None)
    print('has sb-admin css:', '/static/css/sb-admin-2.min.css' in html)
