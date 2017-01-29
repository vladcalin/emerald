from emerald.database import Service, Incident


def update_services_status(session_class):
    statuses = {
        True: "alive",
        False: "dead"
    }

    session = session_class()
    for service in session.query(Service).filter():
        old_status = service.is_alive
        service.update_is_alive()
        current_status = service.is_alive
        if current_status != old_status:

            if current_status is True:
                severity = Incident.SEVERITY_LOW
            else:
                severity = Incident.SEVERITY_HIGH

            incident = Incident.create(severity, "Service {} ({}) changed status from {} to {}".format(
                service.name, service.url, statuses[old_status], statuses[current_status]
            ))
            session.add(incident)

    session.commit()
