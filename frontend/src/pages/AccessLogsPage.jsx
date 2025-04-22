import React, { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import LogCard from "@/components/LogCard";
import { Button } from "@/components/ui/button";
import { fetchPendingLogs } from "@/services/api";

function PendingLogsTab() {
  const [logs, setLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const loadLogs = async (pageNum) => {
    setIsLoading(true);
    try {
      const { logs: fetchedLogs, hasMore: moreAvailable } = await fetchPendingLogs(pageNum);
      setLogs(prevLogs => pageNum === 1 ? fetchedLogs : [...prevLogs, ...fetchedLogs]);
      setHasMore(moreAvailable);
    } catch (error) {
      console.error("Error fetching pending logs:", error);
      // TODO: Show error message to user
    } finally {
      setIsLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    loadLogs(1);
  }, []);

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    loadLogs(nextPage);
  };

  return (
    <div>
      {logs.length === 0 && !isLoading && <p>No pending logs found.</p>}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {logs.map((log) => (
          <LogCard key={log.log_id} log={log} />
        ))}
      </div>
      {isLoading && <p className="text-center mt-4">Loading...</p>}
      {hasMore && !isLoading && (
        <div className="text-center mt-6">
          <Button onClick={handleLoadMore}>Load More</Button>
        </div>
      )}
    </div>
  );
}

function AccessLogsPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Access Logs</h1>
      <Tabs defaultValue="pending" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="pending">Pending</TabsTrigger>
          <TabsTrigger value="today">Today</TabsTrigger>
          <TabsTrigger value="previous">Previous</TabsTrigger>
        </TabsList>
        <TabsContent value="pending" className="mt-4">
          <PendingLogsTab />
        </TabsContent>
        <TabsContent value="today" className="mt-4">
          {/* Content for Today's Logs goes here */}
          <p>Today's logs will be displayed here...</p>
        </TabsContent>
        <TabsContent value="previous" className="mt-4">
          {/* Content for Previous Logs goes here */}
          <p>Previous logs will be displayed here...</p>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default AccessLogsPage; 