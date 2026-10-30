import { Link } from 'react-router-dom';

const Status = ({ code, title, text }) => (
  <div className="container section empty">
    <p className="eyebrow">{code}</p>
    <h1>{title}</h1>
    <p className="muted">{text}</p>
    <Link to="/" className="btn btn-dark">Back to home</Link>
  </div>
);

export const NotFoundPage = () => <Status code="404" title="Page not found" text="The page you are looking for does not exist." />;
export const UnauthorizedPage = () => <Status code="403" title="Access denied" text="You do not have permission to view this page." />;
