import React from 'react';
import { Link } from 'react-router-dom';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// Function to format timestamp (can be moved to utils later)
const formatTimestamp = (isoString) => {
  if (!isoString) return 'N/A';
  try {
    return new Date(isoString).toLocaleString();
  } catch (e) {
    return 'Invalid Date';
  }
};

function LogCard({ log }) {
  // TODO: Determine image URL from backend (currently assumes direct session_id link)
  // Might need adjustment based on actual API response
  const imageUrl = `/admin/image/${log.session_id}`; 

  return (
    <Card className="overflow-hidden">
      <CardHeader className="p-0">
        <img 
          src={imageUrl}
          alt={`Verification for ${log.session_id}`}
          className="w-full h-48 object-cover" // Fixed height, object cover
          // Basic error handling for image loading
          onError={(e) => { e.target.src = 'https://via.placeholder.com/400x300?text=Image+Error'; e.target.alt = 'Image loading error'; }}
        />
      </CardHeader>
      <CardContent className="p-4">
        <CardTitle className="text-sm font-medium mb-1 truncate">Session: {log.session_id?.substring(0, 8)}...</CardTitle>
        <CardDescription className="text-xs text-gray-500 dark:text-gray-400">
          {formatTimestamp(log.timestamp)}
        </CardDescription>
        <div className="mt-2 space-y-1 text-xs">
          <p>Method: <Badge variant="outline">{log.verification_method || 'N/A'}</Badge></p>
          <p>Employee: {log.employee_name || 'N/A'}</p>
          {/* Status badge could be added here if needed */}
        </div>
      </CardContent>
      <CardFooter className="p-4 pt-0">
        {/* Link the whole card or add a specific button/link */} 
        <Link 
          to={`/reviews/${log.session_id}`}
          className="text-sm text-blue-600 hover:underline dark:text-blue-400"
        >
          View Details
        </Link>
      </CardFooter>
    </Card>
  );
}

export default LogCard; 