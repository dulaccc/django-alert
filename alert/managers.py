from datetime import datetime
from collections import defaultdict
from django.db.models import Manager
from alert.utils import ALERT_TYPES, ALERT_BACKENDS, AlertUser


class AlertManager(Manager): pass


class PendingAlertManager(AlertManager):
    """
    Alerts that are ready to send NOW.
    
    This is not the same as unsent alerts; alerts scheduled to be sent in the
    future will not be affected by this manager.
    """
    
    def get_query_set(self, *args, **kwargs):
        qs = super(PendingAlertManager, self).get_query_set(*args, **kwargs)
        return qs.filter(when__lte=datetime.now(), is_sent=False)
    
    
    
    
class AlertPrefsManager(Manager):
    
    def get_user_prefs(self, user):
        if not user.is_authenticated():
            return dict(((notice_type.id, backend.id), False)
                            for notice_type in ALERT_TYPES.values()
                            for backend in ALERT_BACKENDS.values()
                        )
        
            
        alert_prefs = self.get_query_set().filter(user=user)
        
        prefs = {}
        for pref in alert_prefs:
            prefs[pref.alert_type, pref.backend] = pref.preference
        
        for notice_type in ALERT_TYPES.values():
            for backend in ALERT_BACKENDS.values():
                if (notice_type.id, backend.id) not in prefs:
                    default_pref = notice_type.get_default(backend.id)
                    prefs[notice_type.id, backend.id] = default_pref
        return prefs
    
                
    def get_recipients_for_notice(self, notice_type, alert_users):
        """
        Return a list of (<AlertUser> instance, <AlertBackend> instance) objects
        """
        if isinstance(notice_type, basestring):
            notice_type = ALERT_TYPES[notice_type]
        
        if not alert_users: return ()
        
        users = [au.user for au in alert_users if au.user]
        alert_prefs = self.get_query_set().filter(alert_type=notice_type.id).filter(user__in=users)
        
        prefs = {}
        for pref in alert_prefs:
            pref_alert_user = None
            for au in alert_users:
                if au.user and au.user.id == prefs.user_id:
                    pref_alert_user = au
                    break
            prefs[pref_alert_user, pref.backend] = pref.preference
        
        for au in alert_users:
            for backend in ALERT_BACKENDS.values():
                if (au, backend.id) not in prefs:
                    prefs[au, backend.id] = notice_type.get_default(backend.id)
        
        return ((au, ALERT_BACKENDS[backend_id]) for ((au, backend_id), pref) in prefs.items() if pref)
