"""Tests for directory-based auto-switch rule storage and lookup."""

from gitacc_switcher.rules_manager import RulesManager


def make_manager(tmp_path):
    return RulesManager(rules_file=tmp_path / ".gitaccrules")


class TestListRules:
    def test_empty_when_file_missing(self, tmp_path):
        manager = make_manager(tmp_path)
        assert manager.list_rules() == {}

    def test_reads_added_entries(self, tmp_path):
        manager = make_manager(tmp_path)
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        manager.add_rule(work_dir, "work")

        rules = manager.list_rules()
        assert rules == {str(work_dir.resolve()): "work"}

    def test_ignores_blank_lines_and_comments(self, tmp_path):
        rules_file = tmp_path / ".gitaccrules"
        rules_file.write_text("\n# a comment\n" + f"{tmp_path} = personal\n" + "\n")
        manager = RulesManager(rules_file=rules_file)

        assert manager.list_rules() == {str(tmp_path): "personal"}


class TestAddRule:
    def test_creates_file_when_missing(self, tmp_path):
        manager = make_manager(tmp_path)
        assert not manager.rules_file.exists()

        assert manager.add_rule(tmp_path, "work") is True
        assert manager.rules_file.exists()

    def test_normalizes_relative_path(self, tmp_path, monkeypatch):
        sub_dir = tmp_path / "project"
        sub_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        manager = RulesManager(rules_file=tmp_path / "rules")
        manager.add_rule("project", "work")

        assert manager.list_rules() == {str(sub_dir.resolve()): "work"}

    def test_updates_existing_rule_for_same_directory(self, tmp_path):
        manager = make_manager(tmp_path)
        manager.add_rule(tmp_path, "work")
        manager.add_rule(tmp_path, "personal")

        rules = manager.list_rules()
        assert rules[str(tmp_path.resolve())] == "personal"
        assert len(rules) == 1

    def test_supports_multiple_directories(self, tmp_path):
        manager = make_manager(tmp_path)
        work_dir = tmp_path / "work"
        personal_dir = tmp_path / "personal"
        work_dir.mkdir()
        personal_dir.mkdir()

        manager.add_rule(work_dir, "work")
        manager.add_rule(personal_dir, "personal")

        rules = manager.list_rules()
        assert rules[str(work_dir.resolve())] == "work"
        assert rules[str(personal_dir.resolve())] == "personal"


class TestRemoveRule:
    def test_removes_existing_rule(self, tmp_path):
        manager = make_manager(tmp_path)
        manager.add_rule(tmp_path, "work")

        assert manager.remove_rule(tmp_path) is True
        assert manager.list_rules() == {}

    def test_returns_false_when_no_rule_exists(self, tmp_path):
        manager = make_manager(tmp_path)
        assert manager.remove_rule(tmp_path) is False

    def test_leaves_other_rules_intact(self, tmp_path):
        manager = make_manager(tmp_path)
        work_dir = tmp_path / "work"
        personal_dir = tmp_path / "personal"
        work_dir.mkdir()
        personal_dir.mkdir()
        manager.add_rule(work_dir, "work")
        manager.add_rule(personal_dir, "personal")

        manager.remove_rule(work_dir)

        rules = manager.list_rules()
        assert str(work_dir.resolve()) not in rules
        assert rules[str(personal_dir.resolve())] == "personal"


class TestFindMatchingAccount:
    def test_no_match_when_no_rules(self, tmp_path):
        manager = make_manager(tmp_path)
        assert manager.find_matching_account(tmp_path) is None

    def test_exact_directory_match(self, tmp_path):
        manager = make_manager(tmp_path)
        manager.add_rule(tmp_path, "work")

        assert manager.find_matching_account(tmp_path) == "work"

    def test_subdirectory_matches_parent_rule(self, tmp_path):
        manager = make_manager(tmp_path)
        work_dir = tmp_path / "work"
        nested = work_dir / "repo" / "src"
        nested.mkdir(parents=True)
        manager.add_rule(work_dir, "work")

        assert manager.find_matching_account(nested) == "work"

    def test_unrelated_directory_does_not_match(self, tmp_path):
        manager = make_manager(tmp_path)
        work_dir = tmp_path / "work"
        other_dir = tmp_path / "other"
        work_dir.mkdir()
        other_dir.mkdir()
        manager.add_rule(work_dir, "work")

        assert manager.find_matching_account(other_dir) is None

    def test_most_specific_rule_wins(self, tmp_path):
        manager = make_manager(tmp_path)
        work_dir = tmp_path / "work"
        client_dir = work_dir / "client-a"
        client_dir.mkdir(parents=True)
        manager.add_rule(work_dir, "work")
        manager.add_rule(client_dir, "client-a")

        assert manager.find_matching_account(client_dir) == "client-a"
        assert manager.find_matching_account(work_dir) == "work"
        assert manager.find_matching_account(client_dir / "src") == "client-a"
