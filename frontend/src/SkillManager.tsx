import { useState, useMemo } from "react";
import {
  Users,
  TrendingUp,
  Award,
  Clock,
  ChevronDown,
  Plus,
  Search,
  Filter,
  BarChart3
} from "lucide-react";
import "./skill-manager.css";

type SkillStatus = "not-started" | "in-progress" | "completed";

type PersonSkill = {
  skillId: string;
  skillName: string;
  status: SkillStatus;
  completedAt?: string;
  progress: number;
};

type Person = {
  id: string;
  name: string;
  email: string;
  department: string;
  skills: PersonSkill[];
  skillsCompleted: number;
  totalSkills: number;
};

const mockPeople: Person[] = [
  {
    id: "1",
    name: "Alice Johnson",
    email: "alice@example.com",
    department: "Operations",
    skills: [
      { skillId: "lego-rgb", skillName: "LEGO Red-Blue-Green Assembly", status: "completed", completedAt: "2026-07-01", progress: 100 },
      { skillId: "lego-ypo", skillName: "LEGO Yellow-Purple-Orange Assembly", status: "in-progress", progress: 65 },
      { skillId: "precision", skillName: "Precision Handling", status: "not-started", progress: 0 }
    ],
    skillsCompleted: 1,
    totalSkills: 3
  },
  {
    id: "2",
    name: "Bob Smith",
    email: "bob@example.com",
    department: "Manufacturing",
    skills: [
      { skillId: "lego-rgb", skillName: "LEGO Red-Blue-Green Assembly", status: "completed", completedAt: "2026-06-28", progress: 100 },
      { skillId: "lego-ypo", skillName: "LEGO Yellow-Purple-Orange Assembly", status: "completed", completedAt: "2026-07-03", progress: 100 },
      { skillId: "precision", skillName: "Precision Handling", status: "in-progress", progress: 45 }
    ],
    skillsCompleted: 2,
    totalSkills: 3
  },
  {
    id: "3",
    name: "Carol Davis",
    email: "carol@example.com",
    department: "Operations",
    skills: [
      { skillId: "lego-rgb", skillName: "LEGO Red-Blue-Green Assembly", status: "in-progress", progress: 30 },
      { skillId: "lego-ypo", skillName: "LEGO Yellow-Purple-Orange Assembly", status: "not-started", progress: 0 },
      { skillId: "precision", skillName: "Precision Handling", status: "not-started", progress: 0 }
    ],
    skillsCompleted: 0,
    totalSkills: 3
  },
  {
    id: "4",
    name: "David Wilson",
    email: "david@example.com",
    department: "Quality",
    skills: [
      { skillId: "lego-rgb", skillName: "LEGO Red-Blue-Green Assembly", status: "completed", completedAt: "2026-06-25", progress: 100 },
      { skillId: "lego-ypo", skillName: "LEGO Yellow-Purple-Orange Assembly", status: "in-progress", progress: 75 },
      { skillId: "precision", skillName: "Precision Handling", status: "in-progress", progress: 20 }
    ],
    skillsCompleted: 1,
    totalSkills: 3
  }
];

export default function SkillManager() {
  const [people, setPeople] = useState<Person[]>(mockPeople);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDepartment, setSelectedDepartment] = useState<string | null>(null);
  const [expandedPersonId, setExpandedPersonId] = useState<string | null>(null);

  const departments = useMemo(() => {
    const depts = new Set(people.map((p) => p.department));
    return Array.from(depts).sort();
  }, [people]);

  const filteredPeople = useMemo(() => {
    return people.filter((person) => {
      const matchesSearch =
        person.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        person.email.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesDepartment = !selectedDepartment || person.department === selectedDepartment;
      return matchesSearch && matchesDepartment;
    });
  }, [people, searchTerm, selectedDepartment]);

  const stats = useMemo(() => {
    const totalPeople = people.length;
    const totalSkills = people.reduce((sum, p) => sum + p.totalSkills, 0);
    const completedSkills = people.reduce((sum, p) => sum + p.skillsCompleted, 0);
    const avgCompletion = totalPeople > 0 ? ((completedSkills / totalSkills) * 100).toFixed(1) : 0;
    return { totalPeople, totalSkills, completedSkills, avgCompletion };
  }, [people]);

  const getStatusBadge = (status: SkillStatus) => {
    const statusConfig = {
      "not-started": { label: "Not Started", className: "badge-neutral" },
      "in-progress": { label: "In Progress", className: "badge-in-progress" },
      "completed": { label: "Completed", className: "badge-completed" }
    };
    const config = statusConfig[status];
    return <span className={`status-badge ${config.className}`}>{config.label}</span>;
  };

  return (
    <div className="skill-manager">
      <header className="sm-header">
        <div className="sm-header-content">
          <div className="sm-title-block">
            <div className="sm-icon">
              <Users size={24} />
            </div>
            <div>
              <h1>Skill Manager</h1>
              <p>Track team skills and learning progress</p>
            </div>
          </div>
        </div>
      </header>

      <main className="sm-main">
        <section className="sm-stats">
          <StatCard icon={<Users size={20} />} label="Total People" value={stats.totalPeople} color="blue" />
          <StatCard icon={<Award size={20} />} label="Total Skills" value={stats.totalSkills} color="green" />
          <StatCard icon={<TrendingUp size={20} />} label="Completed" value={stats.completedSkills} color="yellow" />
          <StatCard icon={<BarChart3 size={20} />} label="Avg Completion" value={`${stats.avgCompletion}%`} color="teal" />
        </section>

        <section className="sm-controls">
          <div className="sm-search">
            <Search size={18} />
            <input
              type="text"
              placeholder="Search by name or email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="sm-filters">
            <Filter size={18} />
            <select
              value={selectedDepartment || ""}
              onChange={(e) => setSelectedDepartment(e.target.value || null)}
            >
              <option value="">All Departments</option>
              {departments.map((dept) => (
                <option key={dept} value={dept}>
                  {dept}
                </option>
              ))}
            </select>
          </div>
          <button className="sm-add-btn">
            <Plus size={18} />
            <span>Add Person</span>
          </button>
        </section>

        <section className="sm-table-wrapper">
          <div className="sm-table">
            {filteredPeople.length === 0 ? (
              <div className="sm-empty-state">
                <Users size={48} />
                <h3>No people found</h3>
                <p>Try adjusting your search filters</p>
              </div>
            ) : (
              filteredPeople.map((person) => (
                <div key={person.id} className="sm-person-card">
                  <div
                    className="sm-person-header"
                    onClick={() =>
                      setExpandedPersonId(expandedPersonId === person.id ? null : person.id)
                    }
                  >
                    <div className="sm-person-info">
                      <div className="sm-person-avatar">{person.name.charAt(0)}</div>
                      <div>
                        <h3>{person.name}</h3>
                        <p>
                          {person.email} · <span className="dept-badge">{person.department}</span>
                        </p>
                      </div>
                    </div>
                    <div className="sm-person-stats">
                      <div className="sm-skill-count">
                        <strong>{person.skillsCompleted}</strong>
                        <span>of {person.totalSkills}</span>
                      </div>
                      <div className="sm-progress-ring">
                        <svg viewBox="0 0 36 36">
                          <circle
                            cx="18"
                            cy="18"
                            r="16"
                            fill="none"
                            stroke="var(--line)"
                            strokeWidth="2"
                          />
                          <circle
                            cx="18"
                            cy="18"
                            r="16"
                            fill="none"
                            stroke="var(--green)"
                            strokeWidth="2"
                            strokeDasharray={`${(person.skillsCompleted / person.totalSkills) * 100.53} 100.53`}
                            transform="rotate(-90 18 18)"
                          />
                        </svg>
                        <span>{Math.round((person.skillsCompleted / person.totalSkills) * 100)}%</span>
                      </div>
                      <ChevronDown
                        size={20}
                        className={expandedPersonId === person.id ? "expanded" : ""}
                      />
                    </div>
                  </div>

                  {expandedPersonId === person.id && (
                    <div className="sm-person-details">
                      {person.skills.map((skill) => (
                        <div key={skill.skillId} className="sm-skill-row">
                          <div className="sm-skill-info">
                            <span className="sm-skill-name">{skill.skillName}</span>
                            {getStatusBadge(skill.status)}
                          </div>
                          <div className="sm-skill-progress">
                            <div className="progress-bar">
                              <div
                                className="progress-fill"
                                style={{ width: `${skill.progress}%` }}
                              />
                            </div>
                            <span className="progress-text">{skill.progress}%</span>
                          </div>
                          {skill.completedAt && (
                            <div className="sm-completed-date">
                              <Clock size={14} />
                              <span>{new Date(skill.completedAt).toLocaleDateString()}</span>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  color
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className={`sm-stat-card stat-${color}`}>
      <div className="stat-icon">{icon}</div>
      <div className="stat-content">
        <p className="stat-label">{label}</p>
        <h2 className="stat-value">{value}</h2>
      </div>
    </div>
  );
}
