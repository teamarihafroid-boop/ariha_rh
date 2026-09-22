from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.schemas.employee import ProbationEvaluationCreate
from app.services import employee_service
from tests.conftest import _make_employee

TODAY = datetime.now(UTC).date()


def test_probation_prolonge_updates_date_fin(db, employee_a):
    employee_a.date_fin_periode_essai = date(2026, 9, 1)
    db.flush()

    employee_service.record_probation_evaluation(
        db,
        employee_a,
        ProbationEvaluationCreate(
            date_evaluation=date(2026, 8, 25),
            decision="Prolongé",
            nouvelle_date_fin=date(2026, 12, 1),
        ),
    )
    assert employee_a.date_fin_periode_essai == date(2026, 12, 1)


def test_probation_confirme_clears_date_fin(db, employee_a):
    employee_a.date_fin_periode_essai = date(2026, 9, 1)
    db.flush()

    employee_service.record_probation_evaluation(
        db,
        employee_a,
        ProbationEvaluationCreate(date_evaluation=date(2026, 8, 25), decision="Confirmé"),
    )
    assert employee_a.date_fin_periode_essai is None


def test_probation_rompu_clears_date_fin(db, employee_a):
    employee_a.date_fin_periode_essai = date(2026, 9, 1)
    db.flush()

    employee_service.record_probation_evaluation(
        db,
        employee_a,
        ProbationEvaluationCreate(date_evaluation=date(2026, 8, 25), decision="Rompu"),
    )
    assert employee_a.date_fin_periode_essai is None


def test_probation_alerts_flags_employee_with_no_evaluation(db, employee_a):
    employee_a.date_fin_periode_essai = TODAY + timedelta(days=5)
    db.flush()

    alerts = employee_service.probation_alerts(db)
    assert any(a["employee_id"] == employee_a.id for a in alerts)


def test_probation_alerts_one_sided_evaluation_still_alerts(db, employee_a):
    """The prototype's own gap: it silenced the reminder as soon as ANY
    evaluation row existed. This rebuild requires both RH and DG sign-off
    before silencing it."""
    employee_a.date_fin_periode_essai = TODAY + timedelta(days=5)
    db.flush()
    employee_service.record_probation_evaluation(
        db,
        employee_a,
        ProbationEvaluationCreate(
            date_evaluation=TODAY, avis_rh="OK pour moi", evaluateur_rh="RH Test"
        ),
    )

    alerts = employee_service.probation_alerts(db)
    assert any(a["employee_id"] == employee_a.id for a in alerts)


def test_probation_alerts_silenced_once_both_sides_signed_off(db, employee_a):
    employee_a.date_fin_periode_essai = TODAY + timedelta(days=5)
    db.flush()
    employee_service.record_probation_evaluation(
        db,
        employee_a,
        ProbationEvaluationCreate(
            date_evaluation=TODAY,
            avis_rh="OK",
            evaluateur_rh="RH Test",
            avis_dg="OK",
            evaluateur_dg="DG Test",
        ),
    )

    alerts = employee_service.probation_alerts(db)
    assert not any(a["employee_id"] == employee_a.id for a in alerts)


def test_probation_alerts_urgency_levels(db, employee_a, employee_b):
    employee_a.date_fin_periode_essai = TODAY - timedelta(days=1)  # overdue
    employee_b.date_fin_periode_essai = TODAY + timedelta(days=2)  # urgent
    db.flush()

    alerts = {a["employee_id"]: a["urgence"] for a in employee_service.probation_alerts(db)}
    assert alerts[employee_a.id] == "retard"
    assert alerts[employee_b.id] == "urgent"


def test_build_org_chart_direction_heuristic(db, active_status):
    from app.models import Department

    dept_a = Department(nom="Dept A (orgchart test)")
    dept_b = Department(nom="Dept B (orgchart test)")
    dept_c = Department(nom="Dept C (orgchart test)")
    db.add_all([dept_a, dept_b, dept_c])
    db.flush()

    boss = _make_employee(db, dept_a, active_status, nom="Boss", prenom="General")
    r1 = _make_employee(db, dept_a, active_status, nom="R1", prenom="Report")
    r2 = _make_employee(db, dept_b, active_status, nom="R2", prenom="Report")
    r3 = _make_employee(db, dept_c, active_status, nom="R3", prenom="Report")
    for r in (r1, r2, r3):
        r.manager_id = boss.id
    db.flush()

    chart = employee_service.build_org_chart(db)
    direction_ids = {n["id"] for n in chart["direction"]}
    assert boss.id in direction_ids


def test_build_org_chart_cross_department_rapporte_a(db, active_status):
    from app.models import Department

    dept_a = Department(nom="Dept A2 (orgchart test)")
    dept_b = Department(nom="Dept B2 (orgchart test)")
    db.add_all([dept_a, dept_b])
    db.flush()

    manager = _make_employee(db, dept_a, active_status, nom="Manager", prenom="Cross")
    report = _make_employee(db, dept_b, active_status, nom="Report", prenom="Cross")
    report.manager_id = manager.id
    db.flush()

    chart = employee_service.build_org_chart(db)
    dept_b_block = next(d for d in chart["departements"] if d["department_id"] == dept_b.id)
    node = next(n for n in dept_b_block["collaborateurs"] if n["id"] == report.id)
    assert node["rapporte_a"] is not None
    assert node["rapporte_a"]["id"] == manager.id


def test_build_org_chart_niveau_follows_categorie_professionnelle(db, active_status):
    from app.models import Department

    dept = Department(nom="Dept Niveau (orgchart test)")
    db.add(dept)
    db.flush()

    responsable = _make_employee(db, dept, active_status, nom="Chef", prenom="Equipe")
    responsable.categorie_professionnelle = "cadre"
    employe = _make_employee(db, dept, active_status, nom="Bas", prenom="Echelon")
    db.flush()

    chart = employee_service.build_org_chart(db)
    dept_block = next(d for d in chart["departements"] if d["department_id"] == dept.id)
    niveaux = {n["id"]: n["niveau"] for n in dept_block["collaborateurs"]}
    assert niveaux[responsable.id] == "responsable"
    assert niveaux[employe.id] == "employe"


def test_build_org_chart_groups_shared_equipe_under_synthetic_team_node(db, active_status):
    from app.models import Department

    dept = Department(nom="Dept Equipe (orgchart test)")
    db.add(dept)
    db.flush()

    manager = _make_employee(db, dept, active_status, nom="Resp", prenom="Stock")
    driver_1 = _make_employee(db, dept, active_status, nom="Chauffeur1", prenom="Logistique")
    driver_2 = _make_employee(db, dept, active_status, nom="Chauffeur2", prenom="Logistique")
    lone = _make_employee(db, dept, active_status, nom="Solo", prenom="Direct")
    for e in (driver_1, driver_2, lone):
        e.manager_id = manager.id
    driver_1.equipe = "Logistique"
    driver_2.equipe = "Logistique"
    db.flush()

    chart = employee_service.build_org_chart(db)
    dept_block = next(d for d in chart["departements"] if d["department_id"] == dept.id)
    manager_node = next(n for n in dept_block["collaborateurs"] if n["id"] == manager.id)
    team_nodes = [n for n in manager_node["enfants"] if n["niveau"] == "equipe"]
    assert len(team_nodes) == 1
    team = team_nodes[0]
    assert team["full_name"] == "Logistique"
    assert {c["id"] for c in team["enfants"]} == {driver_1.id, driver_2.id}
    assert any(n["id"] == lone.id for n in manager_node["enfants"])


def test_build_org_chart_exposes_open_job_offers_as_postes_ouverts(db, active_status):
    from app.models import Department, JobOffer, JobOfferStatus

    dept = Department(nom="Dept Recrutement (orgchart test)")
    db.add(dept)
    db.flush()
    _make_employee(db, dept, active_status, nom="Titulaire", prenom="Place")

    ouverte = db.query(JobOfferStatus).filter_by(libelle="Ouverte").first()
    if ouverte is None:
        ouverte = JobOfferStatus(libelle="Ouverte", couleur="#43A047")
        db.add(ouverte)
        db.flush()
    pourvue = JobOfferStatus(libelle="Pourvue (orgchart test)", couleur="#0288D1")
    db.add(pourvue)
    db.flush()

    open_offer = JobOffer(titre="Technicien froid", department_id=dept.id, status_id=ouverte.id)
    filled_offer = JobOffer(titre="Poste déjà pourvu", department_id=dept.id, status_id=pourvue.id)
    db.add_all([open_offer, filled_offer])
    db.flush()

    chart = employee_service.build_org_chart(db)
    dept_block = next(d for d in chart["departements"] if d["department_id"] == dept.id)
    titres = [p["titre"] for p in dept_block["postes_ouverts"]]
    assert titres == ["Technicien froid"]


def test_build_org_chart_shows_department_with_only_open_offers(db, active_status):
    """A brand-new department with an open recruitment but no hires yet
    must still appear — it should not require an employee to "unlock" it."""
    from app.models import Department, JobOffer, JobOfferStatus

    empty_dept = Department(nom="Dept Vide Recrutement (orgchart test)")
    db.add(empty_dept)
    db.flush()

    ouverte = db.query(JobOfferStatus).filter_by(libelle="Ouverte").first()
    if ouverte is None:
        ouverte = JobOfferStatus(libelle="Ouverte", couleur="#43A047")
        db.add(ouverte)
        db.flush()

    offer = JobOffer(titre="Premier recrutement", department_id=empty_dept.id, status_id=ouverte.id)
    db.add(offer)
    db.flush()

    chart = employee_service.build_org_chart(db)
    dept_block = next(
        (d for d in chart["departements"] if d["department_id"] == empty_dept.id), None
    )
    assert dept_block is not None
    assert dept_block["department_nom"] == "Dept Vide Recrutement (orgchart test)"
    assert dept_block["collaborateurs"] == []
    assert [p["titre"] for p in dept_block["postes_ouverts"]] == ["Premier recrutement"]
