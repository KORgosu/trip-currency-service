import React from 'react';
import styled from 'styled-components';
import { Link } from 'react-router-dom';

const HeaderContainer = styled.header`
  background: white;
  color: #2c3e50;
  padding: 1rem 2rem;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  
  @media (max-width: 768px) {
    padding: 1rem;
  }
  
  @media (max-width: 480px) {
    padding: 0.75rem;
  }
`;

const HeaderContent = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const Logo = styled(Link)`
  font-size: 1.5rem;
  font-weight: bold;
  color: #2c3e50;
  text-decoration: none;
  
  &:hover {
    opacity: 0.8;
  }
  
  @media (max-width: 480px) {
    font-size: 1.2rem;
  }
`;

const Nav = styled.nav`
  display: flex;
  gap: 2rem;
  
  @media (max-width: 768px) {
    gap: 1rem;
  }
  
  @media (max-width: 480px) {
    gap: 0.5rem;
  }
`;

const NavLink = styled(Link)`
  color: #2c3e50;
  text-decoration: none;
  padding: 0.5rem 1rem;
  border-radius: 5px;
  transition: background-color 0.3s;
  
  &:hover {
    background-color: #f8f9fa;
  }
  
  &.active {
    background-color: #667eea;
    color: white;
  }
  
  @media (max-width: 480px) {
    padding: 0.4rem 0.6rem;
    font-size: 0.9rem;
  }
`;

const Header = () => {
  return (
    <HeaderContainer>
      <HeaderContent>
        <Logo to="/">
          🌍 Trip Currency
        </Logo>
        <Nav>
          <NavLink to="/">홈</NavLink>
          <NavLink to="/comparison">비교</NavLink>
          <NavLink to="/ranking">랭킹</NavLink>
        </Nav>
      </HeaderContent>
    </HeaderContainer>
  );
};

export default Header;
