# Privacy architecture

The MVP obtains only public repositories. It uses no GitHub token, OAuth credential or
AI service. It stores the public URL, commit SHA, run time/state, source paths, declaration
names, import relationships/specifiers, line ranges, counts and limitations. Schema-v2
also stores architecture classifications, configuration-derived rules, violations, cycle
witnesses and **bounded source excerpts**: at most five lines of 240 characters each per
evidence location. Excerpts can include comments or sensitive text present in public
source; they are not automatically redacted. They appear in API responses and exports.
Full source files and Git packfiles exist only in temporary analysis storage, removed
when the run ends. Schema-v1 snapshots have no new excerpts added automatically.

`DELETE /api/v1/analysis/{id}` deletes persisted metadata, the graph and its excerpts after the run has
finished. There is no automatic retention expiry yet. Database backups and exported JSON
are operator-controlled copies and are not removed by the delete endpoint.

Logs contain analysis ID, repository URL, SHA, stage, duration and outcome. Raw Git errors,
source bodies, credentials and exception dumps are not emitted by the analysis worker.
This is single-user local storage; access control, tenant isolation, private repository
credentials and encryption/key-management policies must precede hosted private support.
No training or external AI processing occurs.
