from shutil import which
import subprocess as sp
import json


class UefiSetting:
    def __init__(self, kvdict):
        if which("uefisettings") is None:
            print("uefisettings tool not installed")
            self.kvdict = None
        else:
            self.kvdict = kvdict

    def is_set(self):
        if self.kvdict is None:
            return None

        for k in self.kvdict:
            out = sp.run(
                ["uefisettings", "hii", "get", "--json", k], capture_output=True
            ).stdout.decode()
            try:
                js = json.loads(out)
                if not js["responses"] or len(js["responses"]) == 0:
                    continue

                for response in js["responses"]:
                    if response["question"]["name"] != k:
                        continue

                    answer = response["question"]["answer"]
                    return answer.lower() == self.kvdict[k].lower()
            except Exception as e:
                print("Error parsing uefisettings output: " + str(e))

        return None

    def __str__(self):
        return str(self.kvdict)
