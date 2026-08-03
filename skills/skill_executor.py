class SkillExecutor:
    def __init__(self): self.skills={}
    def register(self,name,skill): self.skills[name]=skill
    def execute(self,name,args):
        if name not in self.skills: raise ValueError(f'Unknown skill {name}')
        return self.skills[name](**args)
