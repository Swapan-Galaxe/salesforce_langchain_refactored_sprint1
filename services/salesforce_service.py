class SalesforceService:
    def __init__(self,sf_client): self.sf=sf_client
    def query(self,soql): return self.sf.query(soql)
    def create(self,obj,payload): return getattr(self.sf,obj).create(payload)
    def update(self,obj,rid,payload): return getattr(self.sf,obj).update(rid,payload)
    def delete(self,obj,rid): return getattr(self.sf,obj).delete(rid)
