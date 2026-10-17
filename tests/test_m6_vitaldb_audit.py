"""Dependency-free checks for VitalDB metadata selection and split integrity."""

import unittest

from examples.m6_vitaldb_audit import parse_metadata


class VitalDBMetadataAuditTests(unittest.TestCase):
    def test_pairing_and_subject_disjointness(self):
        cases = "caseid,subjectid,casestart,caseend\n"
        tracks = "caseid,tname,tid\n"
        # Repeated subjects must always stay in one split.
        for i in range(1, 31):
            subject = (i + 1) // 2
            cases += f"{i},{subject},0,3600\n"
            tracks += f"{i},SNUADC/ART,a{i}\n"
            tracks += f"{i},Solar8000/NIBP_MBP,b{i}\n"
            tracks += f"{i},Solar8000/ART_MBP,c{i}\n"
        parsed = parse_metadata(cases, tracks)
        self.assertEqual(parsed["paired_track_case_count"], 30)
        self.assertEqual(parsed["paired_track_subject_count"], 15)
        by_subject = {}
        for row in parsed["candidates"]:
            old = by_subject.setdefault(row["subjectid"], row["split"])
            self.assertEqual(old, row["split"])
        self.assertEqual(parsed["candidate_12_bed_caseids"],
                         parse_metadata(cases, tracks)["candidate_12_bed_caseids"])

    def test_missing_pair_and_short_case_are_excluded_from_replay(self):
        cases = "caseid,subjectid,casestart,caseend\n1,1,0,2000\n2,2,0,1500\n3,3,0,3000\n"
        tracks = ("caseid,tname,tid\n"
                  "1,SNUADC/ART,a\n1,Solar8000/NIBP_MBP,b\n"
                  "2,SNUADC/ART,c\n2,Solar8000/NIBP_MBP,d\n"
                  "3,SNUADC/ART,e\n")
        parsed = parse_metadata(cases, tracks)
        self.assertEqual(parsed["paired_track_case_count"], 2)
        self.assertNotIn(2, parsed["candidate_12_bed_caseids"])
        self.assertNotIn(3, parsed["candidate_12_bed_caseids"])


if __name__ == "__main__":
    unittest.main()
