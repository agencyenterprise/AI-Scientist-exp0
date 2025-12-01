"use client";

import { useMemo, useState, useCallback, useEffect } from "react";
import type { ResearchRun, UserListItem } from "@/shared/lib/api-adapters";
import { fetchUsers } from "@/shared/lib/api-adapters";

interface UseResearchFilterOptions {
  currentUserName?: string;
}

interface UseResearchFilterReturn {
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  statusFilter: string;
  setStatusFilter: (status: string) => void;
  onlyMine: boolean;
  setOnlyMine: (value: boolean) => void;
  selectedUser: string | null;
  setSelectedUser: (user: string | null) => void;
  uniqueUsers: string[];
  filteredResearchRuns: ResearchRun[];
}

export function useResearchFilter(
  researchRuns: ResearchRun[],
  options: UseResearchFilterOptions = {}
): UseResearchFilterReturn {
  const { currentUserName } = options;

  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [onlyMine, setOnlyMine] = useState(true);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [users, setUsers] = useState<UserListItem[]>([]);

  // Fetch all users on mount
  useEffect(() => {
    let isMounted = true;
    fetchUsers()
      .then(fetchedUsers => {
        if (isMounted) {
          setUsers(fetchedUsers);
        }
      })
      .catch(() => {
        // Silently fail - will show empty user list
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleSetSearchTerm = useCallback((term: string) => {
    setSearchTerm(term);
  }, []);

  const handleSetStatusFilter = useCallback((status: string) => {
    setStatusFilter(status);
  }, []);

  const handleSetOnlyMine = useCallback((value: boolean) => {
    setOnlyMine(value);
    if (value) {
      setSelectedUser(null);
    }
  }, []);

  const handleSetSelectedUser = useCallback((user: string | null) => {
    setSelectedUser(user);
  }, []);

  const uniqueUsers = useMemo(() => {
    return users.map(u => u.name).sort();
  }, [users]);

  const filteredResearchRuns = useMemo(() => {
    let filtered = researchRuns;

    // Filter by user
    if (onlyMine && currentUserName) {
      filtered = filtered.filter(run => run.createdByName === currentUserName);
    } else if (!onlyMine && selectedUser) {
      filtered = filtered.filter(run => run.createdByName === selectedUser);
    }

    // Filter by status
    if (statusFilter !== "all") {
      filtered = filtered.filter(run => run.status === statusFilter);
    }

    // Filter by search term
    if (searchTerm.trim()) {
      const lowerSearch = searchTerm.toLowerCase();
      filtered = filtered.filter(run => {
        const title = run.ideaTitle?.toLowerCase() || "";
        const hypothesis = run.ideaHypothesis?.toLowerCase() || "";
        const runId = run.runId?.toLowerCase() || "";
        const createdBy = run.createdByName?.toLowerCase() || "";
        const stage = run.currentStage?.toLowerCase() || "";

        return (
          title.includes(lowerSearch) ||
          hypothesis.includes(lowerSearch) ||
          runId.includes(lowerSearch) ||
          createdBy.includes(lowerSearch) ||
          stage.includes(lowerSearch)
        );
      });
    }

    return filtered;
  }, [researchRuns, searchTerm, statusFilter, onlyMine, selectedUser, currentUserName]);

  return {
    searchTerm,
    setSearchTerm: handleSetSearchTerm,
    statusFilter,
    setStatusFilter: handleSetStatusFilter,
    onlyMine,
    setOnlyMine: handleSetOnlyMine,
    selectedUser,
    setSelectedUser: handleSetSelectedUser,
    uniqueUsers,
    filteredResearchRuns,
  };
}
