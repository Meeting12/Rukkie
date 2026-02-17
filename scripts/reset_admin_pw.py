from django.contrib.auth import get_user_model
import secrets, string

username = 'Meeting'
User = get_user_model()
user = User.objects.filter(username=username).first()
if not user:
    print('NOUSER')
else:
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*()'
    password = ''.join(secrets.choice(alphabet) for _ in range(16))
    user.set_password(password)
    user.save()
    print('PASSWORD:' + password)
